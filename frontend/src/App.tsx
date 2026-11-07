import {useCallback, useEffect, useState} from 'react'
import type {Appeal, BatchResult, Checklist, ChecklistRow, Config, ConversationDetail, ConversationRow, Evidence, JobDetail, JobRow, Reference} from './types'
import {api} from './api'
import {Assessment, Highlighted} from './Assessment'
import {date, dollars, safeLink, terminal} from './format'
import {ChecklistEditor, newCriterion} from './Checklists'
import {AppealForm, ResolveForm} from './ReviewForms'
import styles from './App.module.css'

function App() {
  const initial = new URLSearchParams(location.search)
  const [view, setView] = useState(initial.get('view') || 'conversations')
  const [conversationId, setConversationId] = useState(initial.get('conversation') || '')
  const [jobId, setJobId] = useState(initial.get('job') || '')
  const [conversations, setConversations] = useState<ConversationRow[]>([]), [checklists, setChecklists] = useState<ChecklistRow[]>([])
  const [checklistId, setChecklistId] = useState(''), [config, setConfig] = useState<Config>()
  const [conversation, setConversation] = useState<ConversationDetail>(), [job, setJob] = useState<JobDetail>(), [jobs, setJobs] = useState<JobRow[]>([])
  const [selected, setSelected] = useState<string[]>([]), [budget, setBudget] = useState('1.00')
  const [error, setError] = useState(''), [notice, setNotice] = useState(''), [busy, setBusy] = useState(false)
  const [importText, setImportText] = useState(''), [showImport, setShowImport] = useState(false)
  const [focus, setFocus] = useState<{ids: string[]; quote?: string}>({ids: []}), [reference, setReference] = useState<{ref: Reference; quote?: string}>()
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
      } catch (e) {if (!cancelled) setError((e as Error).message)}
    }
    void poll(); return () => {cancelled = true; clearTimeout(timer)}
  }, [batchId])
  useEffect(() => {if (focus.ids.length) document.getElementById(`message-${focus.ids[0]}`)?.scrollIntoView({behavior: 'smooth', block: 'center'})}, [focus])
  function chooseConversation(id: string) {setConversationId(id); setJobId(''); setJob(undefined); setNotice('')}
  function chooseJob(j: JobRow) {setConversationId(j.conversation_id); setJobId(j.id); setView('conversations')}
  function evidence(items: Evidence[], ids: string[] = []) {setReference(undefined); setFocus({ids: items.length ? items.map(e => e.message_id) : ids, quote: items[0]?.quote})}
  async function importNow() {
    await act(async () => {
      const result = await api<{created: number; reused: number; conversations: ConversationRow[]}>('/conversations/import', {content: importText})
      await refresh(); chooseConversation(result.conversations[0].id); setSelected(result.conversations.map(c => c.id)); setShowImport(false); setImportText('')
      setNotice(`Imported ${result.created} new revisions; ${result.reused} unchanged records reused.`)
    })
  }
  async function run(ids: string[], force = false) {
    await act(async () => {
      const result = await api<BatchResult>('/evaluations', {conversation_ids: ids, checklist_id: checklistId, request_id: crypto.randomUUID(), budget_usd: Number(budget), force})
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
  return <div className={styles.app}>
    <header className={styles.header}><div><h1>Freedom CQA</h1><span>Conversation evaluation & review</span></div>
      <nav>{['conversations','checklists','history'].map(v => <button key={v} className={view === v ? styles.active : ''} onClick={() => setView(v)}>{v === 'history' ? 'Evaluation history' : v[0].toUpperCase() + v.slice(1)}</button>)}</nav>
      <div className={styles.account}>{config ? <><b>{config.api_key_configured ? 'API configured' : 'API key missing'}</b><span>{dollars(config.ledger.lifetime_committed_usd)} / {dollars(config.ledger.lifetime_limit_usd)} local limit</span></> : 'Connecting…'}</div>
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
      <div className={styles.toolbar}><button onClick={() => setShowImport(!showImport)}>Import conversations</button>
        <select aria-label="Evaluation checklist" value={checklistId} onChange={e => setChecklistId(e.target.value)}>{checklists.map(c => <option key={c.id} value={c.id}>{c.title} · {c.version}</option>)}</select>
        <label>Batch budget $<input aria-label="Batch budget" type="number" min="0.01" step="0.01" value={budget} onChange={e => setBudget(e.target.value)}/></label>
        <button disabled={busy || !selected.length || !checklistId} onClick={() => run(selected)}>Evaluate selected ({selected.length})</button></div>
      {showImport && <section className={styles.importBox}><h2>Import JSON or JSONL</h2><p>Canonical conversations, organizer DEV responses, arrays and diagnostic JSONL are supported. Only conversation data enters evaluation.</p>
        <input aria-label="Conversation file" type="file" accept=".json,.jsonl,application/json" onChange={e => {const file = e.target.files?.[0]; if (file) file.text().then(setImportText).catch(e => setError(e.message))}}/>
        <textarea aria-label="Conversation JSON" rows={9} value={importText} onChange={e => setImportText(e.target.value)} placeholder='{"id":"conversation-1","channel":"agent chat","language":"EN","messages":[…]}'/>
        <button disabled={busy || !importText.trim()} onClick={importNow}>Import</button></section>}
      {batch && <div className={styles.batch}><b>Batch: {batch.jobs.filter(j => terminal.has(j.status)).length}/{batch.jobs.length} finished</b><span>{dollars(batch.committed_usd)} committed / {dollars(batch.budget_usd)} budget</span>{batch.jobs.map(j => <button key={j.id} onClick={() => chooseJob(j)}>{j.id.slice(0, 7)} · {j.status}</button>)}</div>}
      <main className={styles.workspace}><aside className={styles.sidebar}><h2>Conversations ({conversations.length})</h2>
        <label><input type="checkbox" checked={selected.length > 0 && selected.length === conversations.length} onChange={e => setSelected(e.target.checked ? conversations.map(c => c.id) : [])}/> Select all</label>
        {conversations.map(c => <div key={c.id} className={`${styles.conversationRow} ${conversationId === c.id ? styles.selected : ''}`}><input aria-label={`Select ${c.external_id}`} type="checkbox" checked={selected.includes(c.id)} onChange={e => setSelected(old => e.target.checked ? [...old, c.id] : old.filter(id => id !== c.id))}/>
          <button onClick={() => chooseConversation(c.id)}><b>{c.external_id}</b><span>{c.language} · {c.channel} · {c.message_count} messages</span><small>Revision {c.content_hash.slice(0, 7)} · {date(c.created_at)}</small></button></div>)}
        {!conversations.length && <p>Import conversations to begin. No prepared evaluations are loaded.</p>}</aside>
        <section className={styles.transcript}>{source ? <><div className={styles.sectionHeading}><h2>{source.external_id}</h2><span>{source.language} · {source.channel}</span></div>
          <div className={styles.row}><button onClick={() => {setImportText(JSON.stringify(source.content, null, 2)); setShowImport(true)}}>Edit / import new revision</button><button disabled={busy} onClick={() => run([source.id])}>Evaluate this revision</button></div>
          <ReferenceContext source={source} onApplied={async id => {await refresh(); chooseConversation(id)}} onError={setError}/>
          {source.metadata.recording_url && <a href={safeLink(source.metadata.recording_url)} target="_blank" rel="noreferrer">Open original recording</a>}
          {source.channel === 'voice call' && <p className={styles.muted}>Transcript assessment only. Audio, diction and pronunciation have not been analyzed.</p>}
          {source.content.messages.map(m => <article id={`message-${m.id}`} data-testid={`message-${m.id}`} key={m.id} className={`${styles.message} ${styles[m.speaker] || ''} ${focus.ids.includes(m.id) ? styles.highlight : ''}`}>
            <div><b>{m.speaker}</b><span>{m.id} · {m.timestamp}</span></div><p>{focus.ids.includes(m.id) && focus.quote ? <Highlighted text={m.text} quote={focus.quote}/> : m.text}</p></article>)}
          {source.content.references.length > 0 && <details><summary>Attached reference material ({source.content.references.length})</summary>{source.content.references.map(ref => <button key={ref.id} onClick={() => setReference({ref})}>{ref.id}</button>)}</details>}
        </> : <div className={styles.empty}><h2>Choose a conversation</h2><p>Import a file, select a checklist version and run the real evaluator.</p></div>}</section>
        <section className={styles.results}><div className={styles.row}><h2>Assessment</h2><select aria-label="Saved evaluation" value={jobId} onChange={e => setJobId(e.target.value)}><option value="">Choose a saved evaluation</option>{jobs.map(j => <option key={j.id} value={j.id}>{date(j.created_at)} · {j.status} · {j.id.slice(0, 7)}</option>)}</select></div>
          {job ? <Assessment job={job} busy={busy} onRetry={retry} onCancel={() => act(async () => {await api(`/jobs/${job.id}/cancel`, {}); await refreshJob()})} onEvidence={evidence} onReference={(ref, quote) => setReference({ref, quote})} onAppeal={setAppealCriterion} onResolve={setResolveAppeal}/> : <p className={styles.empty}>Run an evaluation or select a saved result. Loading a saved result makes no API call.</p>}
        </section></main></>}
    {reference && <div className={styles.overlay}><section className={styles.dialog}><button className={styles.close} onClick={() => setReference(undefined)}>Close reference</button><h2>{reference.ref.id}</h2><p>{reference.ref.provenance}</p>
      <p>Scope: {reference.ref.scope || 'Explicitly supplied facts'} · Window: {reference.ref.valid_from || 'unspecified'}–{reference.ref.valid_until || 'unspecified'}</p>
      {safeLink(reference.ref.source_url) && <a href={safeLink(reference.ref.source_url)} target="_blank" rel="noreferrer">Original source</a>}
      <p className={styles.sourceText}>{reference.quote ? <Highlighted text={reference.ref.text} quote={reference.quote}/> : reference.ref.text}</p></section></div>}
    {appealCriterion && job && <AppealForm job={job} criterionId={appealCriterion} onClose={() => setAppealCriterion(undefined)} onSaved={async () => {await refreshJob(); setAppealCriterion(undefined)}} onError={setError}/>}
    {resolveAppeal && job && <ResolveForm job={job} appeal={resolveAppeal} onClose={() => setResolveAppeal(undefined)} onSaved={async () => {await refreshJob(); setResolveAppeal(undefined)}} onError={setError}/>}
  </div>
}

function ReferenceContext({source, onApplied, onError}: {source: ConversationDetail; onApplied: (id: string) => Promise<void>; onError: (s: string) => void}) {
  const [packs, setPacks] = useState<{id: string; scope: string; references: Reference[]}[]>([]), [selected, setSelected] = useState(''), [on, setOn] = useState(''), [pending, setPending] = useState(false)
  useEffect(() => {api<typeof packs>('/reference-packs').then(setPacks).catch(e => onError(e.message))}, [onError])
  return <details className={styles.context}><summary>Reference context · {source.reference_count} attached</summary><p>Creates a new conversation revision. Select a matching platform and a known conversation date.</p>
    <select aria-label="Reference pack" value={selected} onChange={e => setSelected(e.target.value)}><option value="">Choose reference pack</option>{packs.map(p => <option key={p.id} value={p.id}>{p.id} · {p.scope}</option>)}</select>
    <label>Known conversation date<input aria-label="Known conversation date" type="date" value={on} onChange={e => setOn(e.target.value)}/></label>
    <button disabled={!selected || !on || pending} onClick={async () => {setPending(true); try {const value = await api<ConversationDetail>(`/conversations/${source.id}/references`, {pack_id: selected, scope: packs.find(p => p.id === selected)!.scope, occurred_on: on}); await onApplied(value.id)} catch (e) {onError((e as Error).message)} finally {setPending(false)}}}>Apply as new revision</button>
    {source.content.knowledge_scope && <p>Selected scope: {source.content.knowledge_scope}; date: {source.content.occurred_on || 'unknown'}</p>}
    {packs.find(p => p.id === selected)?.references.map(r => <p key={r.id}>{r.id} · {r.valid_from}–{r.valid_until} · {r.source_url}</p>)}
  </details>
}
function History({onSelect}: {onSelect: (j: JobRow) => void}) {
  const [jobs, setJobs] = useState<JobRow[]>([]), [error, setError] = useState('')
  useEffect(() => {api<JobRow[]>('/jobs').then(setJobs).catch(e => setError(e.message))}, [])
  return <section className={styles.page}><h2>Evaluation history</h2>{error && <p role="alert">{error}</p>}<p>Every new attempt and human review is preserved. Opening a saved result does not call the API.</p>
    <table><thead><tr><th>Created</th><th>Evaluation</th><th>Status</th><th>Human revisions</th><th>Action</th></tr></thead><tbody>{jobs.map(j => <tr key={j.id}><td>{date(j.created_at)}</td><td>{j.id.slice(0, 8)}</td><td>{j.status}</td><td>{j.review_revision}</td><td><button onClick={() => onSelect(j)}>Open result</button></td></tr>)}</tbody></table>{!jobs.length && <p>No evaluations yet.</p>}</section>
}
export default App
