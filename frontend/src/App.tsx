import {useCallback, useEffect, useState} from 'react'
import type {Appeal, BatchResult, Checklist, ChecklistRow, CitationSelection, Config, ConversationDetail, ConversationRow, Evidence, HighlightRange, JobDetail, JobRow, Reference} from './types'
import {api} from './api'
import {Assessment, Highlighted} from './Assessment'
import {date, dollars, referenceDate, safeLink, terminal} from './format'
import {ChecklistEditor, newCriterion} from './Checklists'
import {AppealForm, ResolveForm} from './ReviewForms'
import {ReferenceContext} from './ReferenceContext'
import styles from './App.module.css'
import {Icon} from './Icon'
import {ConversationQueue} from './ConversationQueue'
import {Recording} from './Recording'
import {AssessmentComparison} from './AssessmentComparison'

function sourceHighlights(text: string, kind: 'dialogue'|'reference', sourceId: string,
  items: ({quote: string} & CitationSelection)[]) {
  const characters = Array.from(text), ranges: HighlightRange[] = []
  let invalid = false
  for (const item of items) {
    const hasSelection = item.source_citation_expected || [item.source_span_id, item.source_id, item.source_kind,
      item.source_field, item.source_start, item.source_end].some(value => value !== undefined)
    if (hasSelection) {
      const start = item.source_start, end = item.source_end
      if (!item.source_span_id || item.source_id !== sourceId || item.source_kind !== kind || item.source_field !== 'text'
          || typeof start !== 'number' || typeof end !== 'number' || !Number.isInteger(start) || !Number.isInteger(end)
          || start < 0 || end <= start || end > characters.length || characters.slice(start, end).join('') !== item.quote) {
        invalid = true
        continue
      }
      ranges.push({start, end, quote: item.quote})
    } else if (item.quote) {
      // Historical/human quote-only citations have no selected offset. Preserve
      // their old lookup behavior; never use it to replace invalid v3 metadata.
      const at = text.indexOf(item.quote)
      if (at >= 0) {
        const start = Array.from(text.slice(0, at)).length
        ranges.push({start, end: start + Array.from(item.quote).length, quote: item.quote})
      }
    }
  }
  return {ranges, invalid}
}

function App() {
  const initial = new URLSearchParams(location.search)
  const [view, setView] = useState(initial.get('view') || 'conversations')
  const [conversationId, setConversationId] = useState(initial.get('conversation') || '')
  const [jobId, setJobId] = useState(initial.get('job') || '')
  const [conversations, setConversations] = useState<ConversationRow[]>([]), [checklists, setChecklists] = useState<ChecklistRow[]>([])
  const [checklistId, setChecklistId] = useState(''), [config, setConfig] = useState<Config>()
  const [conversation, setConversation] = useState<ConversationDetail>(), [job, setJob] = useState<JobDetail>(), [jobs, setJobs] = useState<JobRow[]>([])
  const [selected, setSelected] = useState<string[]>([]), [budget, setBudget] = useState('1.00')
  const [strategy, setStrategy] = useState<'assessor'|'assessor-reviewed'>('assessor')
  const [error, setError] = useState(''), [notice, setNotice] = useState(''), [busy, setBusy] = useState(false)
  const [importText, setImportText] = useState(''), [showImport, setShowImport] = useState(false)
  const [focus, setFocus] = useState<{ids: string[]; items?: Evidence[]}>({ids: []})
  const [reference, setReference] = useState<{ref: Reference; quote?: string; selection?: CitationSelection}>()
  const [appealCriterion, setAppealCriterion] = useState<string>(), [resolveAppeal, setResolveAppeal] = useState<Appeal>()
  const [editor, setEditor] = useState<Checklist>(), [batchId, setBatchId] = useState('')
  const [batch, setBatch] = useState<{budget_usd: number; committed_usd: number; jobs: JobRow[]}>()
  const refresh = useCallback(async () => {
    const [cs, lists, cfg] = await Promise.all([api<ConversationRow[]>('/conversations'), api<ChecklistRow[]>('/checklists'), api<Config>('/config')])
    setConversations(cs); setChecklists(lists); setConfig(cfg)
    setChecklistId(old => old || lists.find(c => c.external_id === cfg.default_checklist.id && c.version === cfg.default_checklist.version)?.id || lists[0]?.id || '')
  }, [])
  async function act(work: () => Promise<void>) {
    setError(''); setBusy(true)
    try {await work()} catch (e) {setError((e as Error).message)} finally {setBusy(false)}
  }
  const refreshJob = async () => {if (jobId) setJob(await api<JobDetail>(`/jobs/${jobId}`))}
  useEffect(() => {refresh().catch(e => setError(e.message))}, [refresh])
  useEffect(() => {
    const query = new URLSearchParams({view}); if (conversationId) query.set('conversation', conversationId); if (jobId) query.set('job', jobId)
    history.replaceState(null, '', `?${query}`)
  }, [view, conversationId, jobId])
  useEffect(() => {
    let cancelled = false
    if (!conversationId) {setConversation(undefined); setJobs([]); return}
    Promise.all([api<ConversationDetail>(`/conversations/${conversationId}`), api<JobRow[]>(`/jobs?conversation_id=${conversationId}`)])
      .then(([c, js]) => {if (!cancelled) {setConversation(c); setJobs(js)}}).catch(e => setError(e.message))
    return () => {cancelled = true}
  }, [conversationId, jobId])
  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout>
    setJob(undefined); setFocus({ids: []}); setReference(undefined)
    if (!jobId) return
    const poll = async () => {
      try {
        const result = await api<JobDetail>(`/jobs/${jobId}`)
        if (cancelled) return
        setJob(result)
        if (!terminal.has(result.status)) timer = setTimeout(poll, 1200)
        else {refresh().catch(e => setError(e.message)); api<JobRow[]>(`/jobs?conversation_id=${result.conversation_id}`).then(setJobs).catch(e => setError(e.message))}
      } catch (e) {if (!cancelled) setError((e as Error).message)}
    }
    void poll(); return () => {cancelled = true; clearTimeout(timer)}
  }, [jobId, refresh])
  useEffect(() => {
    if (!batchId) return
    let cancelled = false
    let timer: ReturnType<typeof setTimeout>
    const poll = async () => {
      try {
        const result = await api<typeof batch>(`/batches/${batchId}`)
        if (cancelled || !result) return
        setBatch(result)
        if (result.jobs.some(j => !terminal.has(j.status))) timer = setTimeout(poll, 1500)
        else setNotice(`Batch finished: ${result.jobs.filter(j => j.status === 'completed').length} completed, ${result.jobs.filter(j => ['failed', 'interrupted'].includes(j.status)).length} failed${result.jobs.some(j => j.status === 'cancelled') ? `, ${result.jobs.filter(j => j.status === 'cancelled').length} cancelled` : ''}.`)
      } catch (e) {if (!cancelled) setError((e as Error).message)}
    }
    void poll(); return () => {cancelled = true; clearTimeout(timer)}
  }, [batchId])
  useEffect(() => {if (focus.ids.length) document.getElementById(`message-${focus.ids[0]}`)?.scrollIntoView({behavior: 'smooth', block: 'center'})}, [focus])
  function chooseConversation(id: string) {setConversationId(id); setJobId(''); setJob(undefined); setNotice('')}
  function chooseJob(j: JobRow) {setConversationId(j.conversation_id); setJobId(j.id); setView('conversations')}
  function evidence(items: Evidence[], ids: string[] = []) {setReference(undefined); setFocus({ids: items.length ? [...new Set(items.map(e => e.message_id))] : ids, items})}
  async function importNow() {
    await act(async () => {
      const result = await api<{created: number; reused: number; conversations: ConversationRow[]}>('/conversations/import', {content: importText})
      await refresh(); chooseConversation(result.conversations[0].id); setSelected(result.conversations.map(c => c.id)); setShowImport(false); setImportText('')
      setNotice(`Imported ${result.created} new revisions; ${result.reused} unchanged records reused.`)
    })
  }
  async function run(ids: string[], force = false) {
    await act(async () => {
      const result = await api<BatchResult>('/evaluations', {conversation_ids: ids, checklist_id: checklistId, request_id: crypto.randomUUID(), budget_usd: Number(budget), strategy, force})
      setBatchId(result.batch_id || ''); setBatch(undefined)
      if (result.job_ids[0]) {const j = await api<JobDetail>(`/jobs/${result.job_ids[0]}`); setConversationId(j.conversation_id); setJobId(j.id)}
      setNotice(result.reused.length === result.job_ids.length ? 'Loaded saved or already active evaluations. No new job was submitted.' : `Queued ${result.job_ids.length - result.reused.length} real API evaluations; reused ${result.reused.length}.`)
    })
  }
  async function retry() {
    if (!job) return
    await act(async () => {
      const result = await api<BatchResult>(`/jobs/${job.id}/retry`, {request_id: crypto.randomUUID(), budget_usd: Number(budget)})
      setBatchId(result.batch_id || ''); setBatch(undefined); setJobId(result.job_ids[0]); setNotice('New billable attempt queued. The previous result is preserved.')
    })
  }
  const source = job?.conversation || conversation
  const referenceHighlight = reference?.quote ? sourceHighlights(reference.ref.text, 'reference', reference.ref.id,
    [{quote: reference.quote, ...reference.selection}]) : undefined
  return <div className={styles.app}>
    <header className={styles.header}>
      <div className={styles.brand}><div className={styles.brandMark} aria-hidden="true">F</div><div><span className={styles.brandName}>FREEDOM<span>CQA</span></span><span className={styles.brandSubtitle}>Conversation intelligence</span></div></div>
      <nav aria-label="Main navigation">{(['conversations','checklists','history'] as const).map(v => <button key={v} className={view === v ? styles.active : ''} aria-current={view === v ? 'page' : undefined} onClick={() => setView(v)}><Icon name={v === 'conversations' ? 'chat' : v === 'checklists' ? 'settings' : 'history'} size={16}/>{v === 'history' ? 'Evaluation history' : v[0].toUpperCase() + v.slice(1)}</button>)}</nav>
      <div className={styles.account}>{config ? <><div><b>{config.api_key_configured ? 'API configured' : 'API key missing'}</b><span>{dollars(config.ledger.lifetime_committed_usd)} / {dollars(config.ledger.lifetime_limit_usd)} local limit</span></div><div className={styles.avatar}><Icon name="shield" size={16}/></div></> : 'Connecting…'}</div>
    </header>
    {error && <div role="alert" className={styles.error}>{error}<button onClick={() => setError('')}>Dismiss</button></div>}
    {notice && <div role="status" className={styles.notice}>{notice}</div>}
    {view === 'checklists' ? <section className={styles.page}><h2>Versioned checklists</h2><p>Saved versions are immutable. Existing evaluations retain their original version.</p>
      <div className={styles.row}><select aria-label="Checklist to edit" value={checklistId} onChange={e => setChecklistId(e.target.value)}>{checklists.map(c => <option key={c.id} value={c.id}>{c.title} · {c.version}</option>)}</select>
        <button onClick={() => {const found = checklists.find(c => c.id === checklistId); if (found) {const c = structuredClone(found.content); c.version += `-revision-${Date.now()}`; setEditor(c)}}}>Edit as new version</button>
        <button onClick={() => setEditor({id: `checklist-${Date.now()}`, version: '1', title: 'New checklist', instructions: [], criteria: [newCriterion()]})}>New checklist</button></div>
      {editor ? <ChecklistEditor value={editor} onChange={setEditor} busy={busy} onSave={() => act(async () => {const saved = await api<ChecklistRow>('/checklists', editor); await refresh(); setChecklistId(saved.id); setEditor(undefined); setNotice('Saved a new immutable checklist version.')})}/> :
        checklists.find(c => c.id === checklistId)?.content.criteria.map(c => <article className={styles.card} key={c.id}><h3>{c.title} <small>{c.weight} points · {c.kind}</small></h3><p>{c.instruction}</p><p>{c.levels.map(l => `${l.value}: ${l.description}`).join(' · ')}</p>{c.na_condition && <p>N/A only when: {c.na_condition}</p>}</article>)}
    </section> : view === 'history' ? <History onSelect={chooseJob}/> : <>
      <section className={styles.intro}><div><div className={styles.eyebrow}>Quality workspace</div><h1>Conversation review</h1><p>Evaluate the conversation. Follow the evidence. Record the decision.</p></div>
        <div className={styles.stats} aria-label="Workspace overview"><div className={styles.stat}><strong>{conversations.length}</strong><span>Conversations</span></div><div className={styles.stat}><strong>{conversations.filter(c => c.channel === 'voice call').length}</strong><span>Call transcripts</span></div><div className={styles.stat}><strong>{new Set(conversations.map(c => c.language)).size}</strong><span>Languages</span></div><div className={styles.stat}><strong>{selected.length}</strong><span>Selected</span></div></div></section>
      <div className={styles.toolbar}><button onClick={() => setShowImport(!showImport)}><Icon name="upload" size={15}/>Import conversations</button>
        <select aria-label="Evaluation checklist" value={checklistId} onChange={e => setChecklistId(e.target.value)}>{checklists.map(c => <option key={c.id} value={c.id}>{c.title} · {c.version}</option>)}</select>
        <label className={styles.depthControl}><span>Assessment depth</span><select aria-label="Assessment depth" aria-describedby={strategy === 'assessor-reviewed' ? 'assessment-depth-help' : undefined} value={strategy} onChange={e => setStrategy(e.target.value as 'assessor'|'assessor-reviewed')}><option value="assessor">Standard</option><option value="assessor-reviewed">Independent review</option></select></label>
        <label>Batch budget $<input aria-label="Batch budget" type="number" min="0.01" step="0.01" value={budget} onChange={e => setBudget(e.target.value)}/></label>
        <button className={styles.primary} disabled={busy || !selected.length || !checklistId} onClick={() => run(selected)}><Icon name="play" size={14}/>Evaluate selected ({selected.length})</button>
        {strategy === 'assessor-reviewed' && <p id="assessment-depth-help" className={styles.depthHint}>New evaluations use additional model calls within the batch budget. Disagreements may still require human review.</p>}</div>
      {showImport && <section className={styles.importBox}><h2>Import JSON or JSONL</h2><p>Canonical conversations, organizer DEV responses, arrays and diagnostic JSONL are supported. Only conversation data enters evaluation.</p>
        <input aria-label="Conversation file" type="file" accept=".json,.jsonl,application/json" onChange={e => {const file = e.target.files?.[0]; if (file) file.text().then(setImportText).catch(e => setError(e.message))}}/>
        <textarea aria-label="Conversation JSON" rows={9} value={importText} onChange={e => setImportText(e.target.value)} placeholder='{"id":"conversation-1","channel":"agent chat","language":"EN","messages":[…]}'/>
        <button disabled={busy || !importText.trim()} onClick={importNow}>Import</button></section>}
      {batch && <div className={styles.batch} role="status"><div className={styles.batchHead}><Icon name="list" size={17}/><div><b>Batch: {batch.jobs.filter(j => terminal.has(j.status)).length}/{batch.jobs.length} finished</b><br/><span>{dollars(batch.committed_usd)} committed / {dollars(batch.budget_usd)} budget</span></div><progress aria-label="Evaluation batch progress" value={batch.jobs.filter(j => terminal.has(j.status)).length} max={batch.jobs.length || 1}/></div>{batch.jobs.map(j => <button key={j.id} onClick={() => chooseJob(j)}><span className={styles.status} data-status={j.status}>{j.status}</span>{j.id.slice(0, 7)}</button>)}</div>}
      <main className={styles.workspace}>
        <ConversationQueue conversations={conversations} selected={selected} current={conversationId} onSelect={setSelected} onChoose={chooseConversation}/>
        <section className={styles.transcript}>{source ? <><div className={styles.sectionHeading}><div><div className={styles.panelLabel}>Source transcript</div><h2>{source.external_id}</h2><span><Icon name={source.channel === 'voice call' ? 'call' : 'chat'} size={12}/>{source.channel === 'voice call' ? 'Voice call' : 'Agent chat'} · {source.content.messages.length} messages</span></div><span className={styles.pill}>{source.language}</span></div>
          <div className={styles.transcriptActions}><button onClick={() => {setImportText(JSON.stringify(source.content, null, 2)); setShowImport(true)}}>Edit / import new revision</button><button disabled={busy} onClick={() => run([source.id])}>Evaluate this revision</button></div>
          <ReferenceContext key={source.id} source={source} onApplied={async id => {await refresh(); setSelected(old => [...new Set(old.map(selectedId => selectedId === source.id ? id : selectedId))]); chooseConversation(id)}} onError={setError}/>
          {source.metadata.recording_url && <Recording key={source.metadata.recording_url} url={source.metadata.recording_url}/>}
          {source.channel === 'voice call' && !source.metadata.recording_url && <p className={styles.muted}>Transcript assessment only. No recording link is available; voice quality has not been analyzed.</p>}
          {source.content.messages.map(m => {
            const selected = (focus.items || []).filter(item => item.message_id === m.id)
            const highlight = sourceHighlights(m.text, 'dialogue', m.id, selected)
            return <article id={`message-${m.id}`} data-testid={`message-${m.id}`} key={m.id} className={`${styles.message} ${styles[m.speaker] || ''} ${focus.ids.includes(m.id) ? styles.highlight : ''}`}>
              <div><b>{m.speaker}</b><span>{m.id} · {m.timestamp}</span></div><p><Highlighted text={m.text} ranges={highlight.ranges}/></p>
              {highlight.invalid && <small role="status">Selected span does not match this preserved source; exact highlighting is unavailable.</small>}
            </article>
          })}
          {source.content.references.length > 0 && <details><summary>Attached reference material ({source.content.references.length})</summary>{source.content.references.map(ref => <button key={ref.id} onClick={() => setReference({ref})}>{ref.id}</button>)}</details>}
        </> : <div className={styles.empty}><div className={styles.emptyIcon}><Icon name="chat" size={24}/></div><h2>Choose a conversation</h2><p>Select a conversation from the queue to read its source transcript and review its assessment.</p>{!conversations.length && <button onClick={() => setShowImport(true)}><Icon name="upload" size={14}/>Import conversations</button>}</div>}</section>
        <section className={styles.results}><div className={styles.resultsHeader}><div className={styles.panelLabel}>Quality assessment</div><h2>Evidence & decisions</h2><select aria-label="Saved evaluation" value={jobId} onChange={e => setJobId(e.target.value)}><option value="">Choose a saved evaluation</option>{jobs.map(j => <option key={j.id} value={j.id}>{date(j.created_at)} · {j.status} · {j.id.slice(0, 7)}</option>)}</select>{job && <p className={styles.muted} style={{marginBottom: 0}}>Evaluated with: {job.checklist.title} · {job.checklist.version}</p>}</div>
          {job ? <><AssessmentComparison key={job.id} job={job} jobs={jobs}/><Assessment job={job} busy={busy} onRetry={retry} onCancel={() => act(async () => {await api(`/jobs/${job.id}/cancel`, {}); await refreshJob()})} onEvidence={evidence} onReference={(ref, quote, selection) => setReference({ref, quote, selection})} onAppeal={setAppealCriterion} onResolve={setResolveAppeal}/></> : <div className={styles.empty}><div className={styles.emptyIcon}><Icon name="list" size={25}/></div><h2>Ready for assessment</h2><p>{source ? 'Evaluate this conversation or open a saved assessment above. Every decision links back to its source evidence.' : 'Choose a conversation to evaluate it against your saved checklist.'}</p><small>Opening saved results makes no API call.</small></div>}
        </section></main></>}
    {reference && <div className={styles.overlay}><section className={styles.dialog}><button className={styles.close} onClick={() => setReference(undefined)}>Close reference</button><h2>{reference.ref.id}</h2><p>{reference.ref.provenance}</p>
      <p>Scope: {reference.ref.scope || 'Explicitly supplied facts'} · {referenceDate(reference.ref)}</p>
      {safeLink(reference.ref.source_url) && <a href={safeLink(reference.ref.source_url)} target="_blank" rel="noreferrer">Original source</a>}
      <p className={styles.sourceText}>{referenceHighlight ? <Highlighted text={reference.ref.text} ranges={referenceHighlight.ranges}/> : reference.ref.text}</p>
      {referenceHighlight?.invalid && <p role="status">Selected span does not match this preserved source; exact highlighting is unavailable.</p>}
    </section></div>}
    {appealCriterion && job && <AppealForm job={job} criterionId={appealCriterion} onClose={() => setAppealCriterion(undefined)} onSaved={async () => {await refreshJob(); setAppealCriterion(undefined)}} onError={setError}/>}
    {resolveAppeal && job && <ResolveForm key={`${job.id}-${resolveAppeal.id}`} job={job} appeal={resolveAppeal} onClose={() => setResolveAppeal(undefined)} onSaved={async () => {await refreshJob(); setResolveAppeal(undefined)}} onError={setError}/>}
  </div>
}

function History({onSelect}: {onSelect: (j: JobRow) => void}) {
  const [jobs, setJobs] = useState<JobRow[]>([]), [error, setError] = useState('')
  useEffect(() => {api<JobRow[]>('/jobs').then(setJobs).catch(e => setError(e.message))}, [])
  return <section className={styles.page}><h2>Evaluation history</h2>{error && <p role="alert">{error}</p>}<p>Every new attempt and human review is preserved. Opening a saved result does not call the API.</p>
    <table><thead><tr><th>Created</th><th>Evaluation</th><th>Status</th><th>Human revisions</th><th>Action</th></tr></thead><tbody>{jobs.map(j => <tr key={j.id}><td>{date(j.created_at)}</td><td>{j.id.slice(0, 8)}</td><td><span className={styles.status} data-status={j.status}>{j.status}</span></td><td>{j.review_revision}</td><td><button onClick={() => onSelect(j)}>Open result</button></td></tr>)}</tbody></table>{!jobs.length && <p>No evaluations yet.</p>}</section>
}
export default App
