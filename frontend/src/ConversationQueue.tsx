import {useEffect, useRef, useState} from 'react'
import type {ConversationRow} from './types'
import {Icon} from './Icon'
import {date} from './format'
import {groupConversationRevisions} from './conversationRevisions'
import styles from './App.module.css'

export function ConversationQueue({conversations, selected, current, onSelect, onChoose, onOpenAssessment}: {
  conversations: ConversationRow[]; selected: string[]; current: string;
  onSelect: (ids: string[]) => void; onChoose: (id: string) => void;
  onOpenAssessment: (jobId: string, revisionId: string) => void;
}) {
  const [query, setQuery] = useState(''), [language, setLanguage] = useState(''), [channel, setChannel] = useState('')
  const [assessmentFilter, setAssessmentFilter] = useState(''), [expanded, setExpanded] = useState<string[]>([])
  const all = useRef<HTMLInputElement>(null)
  const groups = groupConversationRevisions(conversations)
  const languages = [...new Set(groups.map(group => group.latest.language))].sort()
  const matching = groups.filter(({latest: c}) => {
    const assessment = c.latest_assessment
    return c.external_id.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())
      && (!language || c.language === language) && (!channel || c.channel === channel)
      && (!assessmentFilter || (assessmentFilter === 'unassessed' && assessment === null)
        || (assessmentFilter === 'review' && !!assessment && (assessment.review_recommended_count > 0 || (assessment.open_appeals || 0) > 0))
        || (assessmentFilter === 'completed' && assessment?.status === 'completed')
        || (assessmentFilter === 'active' && !!assessment && ['queued', 'running'].includes(assessment.status))
        || (assessmentFilter === 'failed' && !!assessment && ['failed', 'interrupted', 'cancelled'].includes(assessment.status)))
  })
  // Reveal a selected historical result once; collapsing history never changes the open transcript.
  const currentGroup = groups.find(group => group.revisions.some(revision => revision.id === current))
  const currentGroupId = currentGroup?.externalId, currentLatestId = currentGroup?.latest.id
  useEffect(() => {
    if (currentGroupId && currentLatestId !== current) setExpanded(old => old.includes(currentGroupId) ? old : [...old, currentGroupId])
  }, [current, currentGroupId, currentLatestId])
  const isExpanded = (group: typeof groups[number]) => expanded.includes(group.externalId)
  const visible = matching.flatMap(group => isExpanded(group) ? group.revisions : [group.latest])
  const picked = new Set(selected), selectedVisible = visible.filter(c => picked.has(c.id)).length
  useEffect(() => {if (all.current) all.current.indeterminate = selectedVisible > 0 && selectedVisible < visible.length}, [selectedVisible, visible.length])
  const toggleVisible = (checked: boolean) => {
    const visibleIds = new Set(visible.map(c => c.id))
    onSelect(checked ? [...new Set([...selected, ...visibleIds])] : selected.filter(id => !visibleIds.has(id)))
  }
  function revisionRow(c: ConversationRow, latest: boolean) {
    const assessment = c.latest_assessment
    const savedLabel = assessment === undefined ? 'Assessment status unavailable' : assessment === null ? 'Not assessed'
      : assessment.status === 'completed' ? assessment.total === null ? 'Saved · no numeric grade'
        : `${assessment.total}/100${assessment.provisional ? ' · Provisional' : ''}`
      : `Latest attempt: ${assessment.status}`
    return <div key={c.id} data-testid={`queue-revision-${c.id}`} className={`${styles.conversationRow} ${!latest ? styles.olderRevision : ''} ${current === c.id ? styles.selected : ''}`}>
      <input aria-label={`Select ${c.external_id}${latest ? '' : ` revision ${c.content_hash.slice(0, 7)}`}`} type="checkbox" checked={picked.has(c.id)} onChange={e => onSelect(e.target.checked ? [...new Set([...selected, c.id])] : selected.filter(id => id !== c.id))}/>
      <div className={styles.conversationBody}>
        <button aria-current={current === c.id ? 'true' : undefined} onClick={() => onChoose(c.id)}><b>{c.external_id}</b>
          <span><Icon name={c.channel === 'voice call' ? 'call' : 'chat'} size={11}/>{c.language} · {c.channel === 'voice call' ? 'Call' : 'Chat'} · {c.message_count} messages</span>
          <small>{latest ? 'Latest' : 'Earlier'} revision {c.content_hash.slice(0, 7)} · {date(c.created_at)}</small>
        </button>
        <span className={styles.queueAssessment} data-status={assessment?.status || 'unassessed'}>{savedLabel}</span>
        {!!assessment?.review_recommended_count && <small className={styles.queueReview}>{assessment.review_recommended_count} review recommendation{assessment.review_recommended_count === 1 ? '' : 's'}</small>}
        {!!assessment?.open_appeals && <small className={styles.queueReview}>{assessment.open_appeals} open appeal{assessment.open_appeals === 1 ? '' : 's'}</small>}
        {assessment && <button className={styles.openAssessment} aria-label={`Open assessment for ${c.external_id} revision ${c.content_hash.slice(0, 7)}`} onClick={() => onOpenAssessment(assessment.id, c.id)}>{assessment.status === 'completed' ? 'Open saved result' : 'Open attempt'} <span aria-hidden="true">↗</span></button>}
      </div>
    </div>
  }
  return <aside className={styles.sidebar} aria-label="Conversation queue">
    <div className={styles.queueHeading}><h2>Conversation queue</h2><span className={styles.count}>{groups.length}</span></div>
    <p className={styles.queueHint}>Latest revisions · {conversations.length} saved revisions in history</p>
    <div className={styles.search}><Icon name="search" size={15}/><input type="search" aria-label="Search conversations" placeholder="Search conversation ID" value={query} onChange={e => setQuery(e.target.value)}/></div>
    <div className={styles.filters}>
      <select aria-label="Filter by language" value={language} onChange={e => setLanguage(e.target.value)}><option value="">All languages</option>{languages.map(l => <option key={l} value={l}>{l}</option>)}</select>
      <select aria-label="Filter by channel" value={channel} onChange={e => setChannel(e.target.value)}><option value="">All channels</option><option value="agent chat">Chat</option><option value="voice call">Call</option></select>
      <select className={styles.queueReviewFilter} aria-label="Filter by assessment" value={assessmentFilter} onChange={e => setAssessmentFilter(e.target.value)}><option value="">All assessments</option><option value="review">Review recommended / appeals</option><option value="unassessed">Not assessed</option><option value="completed">Completed</option><option value="active">Queued / running</option><option value="failed">Failed / stopped</option></select>
    </div>
    <div className={styles.queueSelection}><label><input ref={all} type="checkbox" disabled={!visible.length} checked={visible.length > 0 && selectedVisible === visible.length} onChange={e => toggleVisible(e.target.checked)}/> Select visible</label>
      {selected.length ? <button className={styles.quiet} onClick={() => onSelect([])} aria-label="Clear conversation selection">Clear ({selected.length})</button> : <span>{matching.length} shown</span>}</div>
    {selected.length > selectedVisible && <p className={styles.queueHint}>{selected.length - selectedVisible} selected revision(s) are hidden by filters or history.</p>}
    <div className={styles.queueItems}>{matching.map(group => <div key={group.externalId} className={styles.revisionGroup}>
      {revisionRow(group.latest, true)}
      {group.revisions.length > 1 && <button className={styles.revisionToggle} aria-expanded={isExpanded(group)} aria-label={`Revision history for ${group.externalId}`}
        onClick={() => {if (isExpanded(group)) setExpanded(old => old.filter(id => id !== group.externalId))
          else setExpanded(old => [...old, group.externalId])}}>{isExpanded(group) ? 'Hide' : 'Show'} {group.revisions.length - 1} earlier revision{group.revisions.length > 2 ? 's' : ''}</button>}
      {isExpanded(group) && group.revisions.slice(1).map(c => revisionRow(c, false))}
    </div>)}</div>
    {!visible.length && <div className={styles.empty}><Icon name="search" size={23}/><p>{conversations.length ? 'No conversations match these filters.' : 'Your review queue is empty. Import conversations to begin.'}</p>
      {conversations.length > 0 && <button onClick={() => {setQuery(''); setLanguage(''); setChannel(''); setAssessmentFilter('')}}>Clear filters</button>}</div>}
  </aside>
}
