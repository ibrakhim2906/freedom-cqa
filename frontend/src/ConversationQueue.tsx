import {useEffect, useRef, useState} from 'react'
import type {ConversationRow} from './types'
import {Icon} from './Icon'
import styles from './App.module.css'

export function ConversationQueue({conversations, selected, current, onSelect, onChoose}: {
  conversations: ConversationRow[]; selected: string[]; current: string;
  onSelect: (ids: string[]) => void; onChoose: (id: string) => void;
}) {
  const [query, setQuery] = useState(''), [language, setLanguage] = useState(''), [channel, setChannel] = useState('')
  const all = useRef<HTMLInputElement>(null)
  const languages = [...new Set(conversations.map(c => c.language))].sort()
  const visible = conversations.filter(c => c.external_id.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())
    && (!language || c.language === language) && (!channel || c.channel === channel))
  const picked = new Set(selected), selectedVisible = visible.filter(c => picked.has(c.id)).length
  useEffect(() => {if (all.current) all.current.indeterminate = selectedVisible > 0 && selectedVisible < visible.length}, [selectedVisible, visible.length])
  const toggleVisible = (checked: boolean) => {
    const visibleIds = new Set(visible.map(c => c.id))
    onSelect(checked ? [...new Set([...selected, ...visibleIds])] : selected.filter(id => !visibleIds.has(id)))
  }
  return <aside className={styles.sidebar} aria-label="Conversation queue">
    <div className={styles.queueHeading}><h2>Conversation queue</h2><span className={styles.count}>{conversations.length}</span></div>
    <div className={styles.search}><Icon name="search" size={15}/><input type="search" aria-label="Search conversations" placeholder="Search conversation ID" value={query} onChange={e => setQuery(e.target.value)}/></div>
    <div className={styles.filters}>
      <select aria-label="Filter by language" value={language} onChange={e => setLanguage(e.target.value)}><option value="">All languages</option>{languages.map(l => <option key={l} value={l}>{l}</option>)}</select>
      <select aria-label="Filter by channel" value={channel} onChange={e => setChannel(e.target.value)}><option value="">All channels</option><option value="agent chat">Chat</option><option value="voice call">Call</option></select>
    </div>
    <div className={styles.queueSelection}><label><input ref={all} type="checkbox" disabled={!visible.length} checked={visible.length > 0 && selectedVisible === visible.length} onChange={e => toggleVisible(e.target.checked)}/> Select visible</label>
      {selected.length ? <button className={styles.quiet} onClick={() => onSelect([])} aria-label="Clear conversation selection">Clear ({selected.length})</button> : <span>{visible.length} shown</span>}</div>
    <div className={styles.queueItems}>{visible.map(c => <div key={c.id} className={`${styles.conversationRow} ${current === c.id ? styles.selected : ''}`}>
      <input aria-label={`Select ${c.external_id}`} type="checkbox" checked={picked.has(c.id)} onChange={e => onSelect(e.target.checked ? [...selected, c.id] : selected.filter(id => id !== c.id))}/>
      <button aria-current={current === c.id ? 'true' : undefined} onClick={() => onChoose(c.id)}><b>{c.external_id}</b>
        <span><Icon name={c.channel === 'voice call' ? 'call' : 'chat'} size={11}/>{c.language} · {c.channel === 'voice call' ? 'Call' : 'Chat'} · {c.message_count} messages</span>
        <small>Source revision {c.content_hash.slice(0, 7)}</small></button>
    </div>)}</div>
    {!visible.length && <div className={styles.empty}><Icon name="search" size={23}/><p>{conversations.length ? 'No conversations match these filters.' : 'Your review queue is empty. Import conversations to begin.'}</p>
      {conversations.length > 0 && <button onClick={() => {setQuery(''); setLanguage(''); setChannel('')}}>Clear filters</button>}</div>}
  </aside>
}
