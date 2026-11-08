import {useCallback, useEffect, useState} from 'react'
import type {Appeal, BatchResult, Checklist, ChecklistRow, CitationSelection, Config, ConversationDetail, ConversationRow, Evidence, HighlightRange, JobDetail, JobRow, Reference} from './types'
import {api} from './api'
import {Assessment, Highlighted} from './Assessment'
import {date, dollars, referenceDate, safeLink, terminal} from './format'
import {ChecklistEditor, newCriterion} from './Checklists'
import {AppealForm, ResolveForm} from './ReviewForms'
import {ReferenceContext} from './ReferenceContext'
import {referenceTitle} from './CustomReferenceApi'
import styles from './App.module.css'
import {Icon} from './Icon'
import {ConversationQueue} from './ConversationQueue'
import {Recording} from './Recording'
import {AssessmentComparison} from './AssessmentComparison'
import {groupConversationRevisions} from './conversationRevisions'
import {Modal} from './Modal'
import {currentChecklistId, visibleChecklists} from './checklistCatalog'
import {SetupHelp} from './SetupHelp'
import {TextImport} from './TextImport'
import {ChecklistRules} from './ChecklistRules'
import exampleText from '../../examples/judge-example.json?raw'

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

function reviewLayout(): 'review'|'split' {return window.matchMedia('(min-width: 1200px)').matches ? 'split' : 'review'}

function reviewStatus(status: string, isDemo = false) {
  if (isDemo) return 'Учебный разбор'
  const labels: Record<string, string> = {queued: 'В очереди', running: 'Выполняется', completed: 'Завершена', failed: 'С ошибкой', cancelled: 'Отменена', interrupted: 'Прервана'}
  return labels[status] || 'Неизвестный статус'
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
  const [detailTab, setDetailTab] = useState<'transcript'|'review'|'split'>(initial.get('job') ? reviewLayout() : 'transcript')
  const [runIds, setRunIds] = useState<string[]>([])
  const [retryReview, setRetryReview] = useState(false)
  const [importFileName, setImportFileName] = useState('')
  const [importMode, setImportMode] = useState<'text'|'file'>('text')
  const [showSetup, setShowSetup] = useState(false)
  const [importedIds, setImportedIds] = useState<string[]>([])
  const [exampleId, setExampleId] = useState('')
  const [focus, setFocus] = useState<{ids: string[]; items?: Evidence[]}>({ids: []})
  const [reference, setReference] = useState<{ref: Reference; quote?: string; selection?: CitationSelection}>()
  const [appealCriterion, setAppealCriterion] = useState<string>(), [resolveAppeal, setResolveAppeal] = useState<Appeal>()
  const [editor, setEditor] = useState<Checklist>(), [batchId, setBatchId] = useState('')
  const [batch, setBatch] = useState<{budget_usd: number; committed_usd: number; jobs: JobRow[]}>()
  const refresh = useCallback(async () => {
    const [cs, lists, cfg] = await Promise.all([api<ConversationRow[]>('/conversations'), api<ChecklistRow[]>('/checklists'), api<Config>('/config')])
    setConversations(cs); setChecklists(lists); setConfig(cfg)
    setChecklistId(old => currentChecklistId(lists, cfg.default_checklist.id, old, cfg.default_checklist.version))
    return {lists, cfg, cs}
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
        else {setNotice(`Проверка завершена. Успешно: ${result.jobs.filter(j => j.status === 'completed').length}. С ошибкой: ${result.jobs.filter(j => ['failed', 'interrupted'].includes(j.status)).length}. Отменено: ${result.jobs.filter(j => j.status === 'cancelled').length}.`); refresh().catch(e => setError(e.message))}
      } catch (e) {if (!cancelled) setError((e as Error).message)}
    }
    void poll(); return () => {cancelled = true; clearTimeout(timer)}
  }, [batchId, refresh])
  useEffect(() => {
    if (!focus.ids.length || detailTab === 'review') return
    const message = document.getElementById(`message-${focus.ids[0]}`)
    message?.focus({preventScroll: true})
    message?.scrollIntoView({behavior: 'smooth', block: 'center'})
  }, [focus, detailTab])
  function chooseConversation(id: string) {
    const saved = conversations.find(c => c.id === id)?.latest_assessment
    if (conversationId !== id || jobId !== (saved?.id || '')) {
      setConversation(undefined); setJob(undefined); setJobs([])
    }
    setConversationId(id); setJobId(saved?.id || '')
    setDetailTab(saved ? reviewLayout() : 'transcript'); setNotice(''); setFocus({ids: []})
  }
  function chooseJob(j: Pick<JobRow, 'id'|'conversation_id'>) {
    if (conversationId !== j.conversation_id || jobId !== j.id) {setConversation(undefined); setJob(undefined); setJobs([])}
    setConversationId(j.conversation_id); setJobId(j.id); setDetailTab(reviewLayout()); setView('conversations'); setNotice('')
  }
  function evidence(items: Evidence[], ids: string[] = []) {setDetailTab(old => old === 'split' ? 'split' : 'transcript'); setReference(undefined); setFocus({ids: items.length ? [...new Set(items.map(e => e.message_id))] : ids, items})}
  async function importNow(content: string = importText) {
    await act(async () => {
      const result = await api<{created: number; reused: number; conversations: ConversationRow[]}>('/conversations/import', {content})
      await refresh(); chooseConversation(result.conversations[0].id); setSelected([result.conversations[0].id]); setShowImport(false); setImportText('')
      setImportedIds([...new Set(result.conversations.map(c => c.id))]); setView('conversations')
      setImportFileName(''); setNotice(`Данные загружены. Добавлено: ${result.created}, уже сохранено: ${result.reused}. ${result.conversations.length > 1 ? 'Открыт первый диалог. ' : ''}Нажмите «Начать проверку» вверху диалога.`)
    })
  }
  async function tryExample() {
    setShowSetup(false)
    await act(async () => {
      const result = await api<{conversation_id: string; job_id: string; checklist_id: string}>('/demo/open', {})
      await refresh()
      setChecklistId(result.checklist_id)
      setStrategy('assessor'); setBudget('1.00'); setSelected([]); setImportedIds([])
      if (conversationId !== result.conversation_id || jobId !== result.job_id) {setConversation(undefined); setJob(undefined); setJobs([])}
      setConversationId(result.conversation_id); setJobId(result.job_id)
      setView('conversations'); setDetailTab(reviewLayout()); setExampleId(result.conversation_id)
      setRetryReview(false); setRunIds([]); setFocus({ids: []})
      setNotice('Учебный разбор открыт. Оценка, обоснования и цитаты доступны без API-ключа.')
    })
  }
  function addChecklist() {
    setShowSetup(false); setRunIds([]); setRetryReview(false); setView('checklists')
    setEditor({id: `checklist-${Date.now()}`, version: '1', title: '', instructions: [], criteria: [newCriterion()]})
  }
  async function run(ids: string[], force = false) {
    await act(async () => {
      const result = await api<BatchResult>('/evaluations', {conversation_ids: ids, checklist_id: checklistId, request_id: crypto.randomUUID(), budget_usd: Number(budget), strategy, force})
      setRunIds([]); setDetailTab(reviewLayout())
      setBatchId(result.batch_id || ''); setBatch(undefined)
      if (result.job_ids[0]) {const j = await api<JobDetail>(`/jobs/${result.job_ids[0]}`); setConversationId(j.conversation_id); setJobId(j.id)}
      setNotice(result.reused.length === result.job_ids.length ? 'Открыты сохранённые результаты. Дополнительных расходов нет.' : `Новых проверок: ${result.job_ids.length - result.reused.length}. Открыто сохранённых результатов: ${result.reused.length}.`)
    })
  }
  async function retry() {
    if (!job) return
    await act(async () => {
      const result = await api<BatchResult>(`/jobs/${job.id}/retry`, {request_id: crypto.randomUUID(), budget_usd: Number(budget)})
      setRetryReview(false)
      setBatchId(result.batch_id || ''); setBatch(undefined); setJobId(result.job_ids[0]); setNotice('Началась повторная платная проверка. Предыдущий результат сохранён.')
    })
  }
  const source = job?.conversation || conversation
  const selectedIsOpen = selected.length === 1 && selected[0] === conversationId
  const canSelectImported = importedIds.length > 1 && selected.length === 1 && selected[0] === importedIds[0]
  const availableChecklists = visibleChecklists(checklists, config?.default_checklist.id || '', config?.default_checklist.version)
  const latestConversations = groupConversationRevisions(conversations).map(group => group.latest)
  const remainingAllowance = config ? Math.max(0, config.ledger.lifetime_limit_usd - config.ledger.lifetime_committed_usd) : 0
  const reviewReady = !!config?.api_key_configured && remainingAllowance > 0
  const savedReview = !retryReview && runIds.length === 1 ? jobs.find(j => j.conversation_id === runIds[0] && j.checklist_id === checklistId && j.status === 'completed') : undefined
  const referenceHighlight = reference?.quote ? sourceHighlights(reference.ref.text, 'reference', reference.ref.id,
    [{quote: reference.quote, ...reference.selection}]) : undefined
  return <div className={styles.app}>
    <header className={styles.header}>
      <div className={styles.brand}><div className={styles.brandMark} aria-hidden="true">F</div><span className={styles.brandName}>Freedom<span>CQA</span></span></div>
      <nav aria-label="Основная навигация">{(['conversations','checklists','history'] as const).map(v => <button key={v} className={view === v ? styles.active : ''} aria-current={view === v ? 'page' : undefined} onClick={() => setView(v)}><Icon name={v === 'conversations' ? 'chat' : v === 'checklists' ? 'settings' : 'history'} size={16}/>{v === 'history' ? 'История оценок' : v === 'checklists' ? 'Критерии оценки' : 'Диалоги'}</button>)}</nav>
      <button className={styles.helpButton} onClick={() => setShowSetup(true)}>Настройка и помощь</button>
    </header>
    {config && !reviewReady && <div className={styles.setupBanner}><span>{!config.api_key_configured ? 'Готовый пример доступен бесплатно. API-ключ нужен только для новых проверок.' : 'Достигнут установленный лимит расходов. Готовый пример и сохранённые результаты доступны.'}</span><button onClick={() => setShowSetup(true)}>Настроить новые проверки</button></div>}
    {error && <div role="alert" className={styles.error}>{error}<button onClick={() => setError('')}>Закрыть</button></div>}
    {notice && <div role="status" className={`${styles.notice} ${styles.dismissibleNotice}`}><span>{notice}</span><button aria-label="Закрыть уведомление" onClick={() => setNotice('')}><Icon name="close" size={16}/></button></div>}
    {view === 'checklists' ? <section className={styles.page}><div className={styles.checklistPageHeading}><div><h1>Критерии оценки</h1><p>Выберите, по каким критериям оценивать диалоги, или создайте свой чек-лист.</p></div>{editor ? <button onClick={() => setEditor(undefined)}>Отменить изменения</button> : <button className={styles.primary} onClick={() => setEditor({id: `checklist-${Date.now()}`, version: '1', title: '', instructions: [], criteria: [newCriterion()]})}><Icon name="list" size={16}/>Создать чек-лист</button>}</div>
      {!editor && <div className={styles.row}><label>Чек-лист<select aria-label="Выбор чек-листа" value={checklistId} onChange={e => setChecklistId(e.target.value)}>{availableChecklists.map(c => <option key={c.id} value={c.id}>{c.title}{c.external_id === config?.default_checklist.id ? ' (основной)' : ''}</option>)}</select></label>
        <button onClick={() => {const found = checklists.find(c => c.id === checklistId); if (found) {const c = structuredClone(found.content); c.id = `checklist-${crypto.randomUUID()}`; c.version = '1'; c.title += ' — копия'; setEditor(c)}}}>Создать копию</button>
        <span className={styles.muted}>В прежних результатах сохраняются исходные критерии оценки.</span></div>}
      {editor ? <ChecklistEditor value={editor} onChange={setEditor} busy={busy} onSave={() => act(async () => {const saved = await api<ChecklistRow>('/checklists', editor); const {lists, cfg} = await refresh(); setChecklistId(currentChecklistId(lists, cfg.default_checklist.id, saved.id, cfg.default_checklist.version)); setEditor(undefined); setNotice('Чек-лист сохранён. Его можно выбрать перед проверкой диалога.')})}/> : <>
        {checklists.find(c => c.id === checklistId) && <ChecklistRules checklist={checklists.find(c => c.id === checklistId)!.content}/>}</>}
    </section> : view === 'history' ? <History onSelect={chooseJob}/> : <>
      <section className={styles.pageHeading}><div><h1>Диалоги <span>{latestConversations.length}</span></h1><p>Выберите диалог, чтобы посмотреть оценку и её обоснование.</p></div>
        <div className={styles.pageActions}><button disabled={busy} onClick={tryExample}><Icon name="play" size={16}/>Открыть пример</button><button className={styles.primary} onClick={() => setShowImport(true)}><Icon name="upload" size={16}/>Загрузить данные</button></div></section>
      {selected.length > 0 && (!selectedIsOpen || canSelectImported) && <div className={styles.selectionBar}><span>Выбрано: <b>{selected.length}</b></span><button className={styles.quiet} onClick={() => setSelected([])}>Снять выделение</button>{canSelectImported && <button className={styles.quiet} onClick={() => setSelected(importedIds)}>Выбрать все загруженные: {importedIds.length}</button>}{!selectedIsOpen && <button className={styles.primary} disabled={busy || !checklistId} onClick={() => setRunIds(selected)}>{selected.length === 1 ? 'Проверить выбранный диалог' : 'Проверить выбранные'}</button>}</div>}
      {batch && <div className={styles.batch} role="status"><div className={styles.batchHead}><Icon name="list" size={17}/><div><b>Завершено: {batch.jobs.filter(j => terminal.has(j.status)).length} из {batch.jobs.length}</b><br/><span>Расходы: {dollars(batch.committed_usd)} · Лимит: {dollars(batch.budget_usd)}</span></div><progress aria-label="Ход проверки выбранных диалогов" value={batch.jobs.filter(j => terminal.has(j.status)).length} max={batch.jobs.length || 1}/></div>{batch.jobs.map(j => <button key={j.id} onClick={() => chooseJob(j)}><span className={styles.status} data-status={j.status}>{reviewStatus(j.status, j.is_demo)}</span>{j.id.slice(0, 7)}</button>)}</div>}
      <main className={`${styles.workspace} ${conversationId ? styles.hasConversation : ''}`}>
        <ConversationQueue conversations={conversations} selected={selected} current={conversationId} onSelect={setSelected} onChoose={chooseConversation}
          onOpenAssessment={(id, revisionId) => chooseJob({id, conversation_id: revisionId})}/>
        <div className={styles.detailPane}>
          {conversationId ? <>
            <div className={styles.detailHeading}>
              <button className={styles.backToList} onClick={() => {setConversationId(''); setJobId(''); setConversation(undefined); setJob(undefined)}}><span aria-hidden="true">←</span> Все диалоги</button>
              <div className={styles.detailTitle}><div><h2>{source ? source.display_title || (source.channel === 'voice call' ? 'Расшифровка звонка' : 'Чат с клиентом') : 'Загрузка…'}</h2>{source && <p>{source.channel === 'voice call' ? 'Расшифровка звонка' : 'Чат'} · {source.language} · Сообщений: {source.content.messages.length}</p>}</div>
                {source && <button className={styles.primary} disabled={busy || !checklistId} onClick={() => setRunIds([source.id])}><Icon name={job ? 'settings' : 'play'} size={14}/>{job ? 'Параметры проверки' : 'Начать проверку'}</button>}</div>
              <div className={styles.detailTabs} aria-label="Варианты просмотра">
                <button aria-pressed={detailTab === 'transcript'} className={detailTab === 'transcript' ? styles.activeDetailTab : ''} onClick={() => setDetailTab('transcript')}><Icon name="chat" size={16}/>Текст диалога</button>
                <button aria-pressed={detailTab === 'review'} className={detailTab === 'review' ? styles.activeDetailTab : ''} onClick={() => setDetailTab('review')}><Icon name="list" size={16}/>Результат проверки</button>
                <button aria-pressed={detailTab === 'split'} className={`${styles.splitButton} ${detailTab === 'split' ? styles.activeDetailTab : ''}`} onClick={() => setDetailTab('split')}>Рядом с диалогом</button>
              </div>
            </div>
            <div className={`${styles.detailContent} ${detailTab === 'split' ? styles.splitContent : ''}`}>
            <section aria-label="Текст диалога" hidden={detailTab === 'review'} className={styles.transcript}>
              {detailTab === 'split' && <h3 className={styles.paneTitle}>Текст диалога</h3>}
              {source ? <>
                <details className={styles.conversationDetails}><summary>Сведения о диалоге</summary>
                  <p>Исходный ID: {source.external_id}<br/>Сохранено: {date(source.created_at)} · Версия {source.content_hash.slice(0, 7)}</p>
                  <button onClick={() => {setImportText(JSON.stringify({...source.content,
                    ...((source.metadata.recording_url || source.resolved_recording?.url) ? {recording_url: source.metadata.recording_url || source.resolved_recording?.url} : {})}, null, 2)); setImportFileName(''); setImportMode('file'); setShowImport(true)}}>Создать копию</button>
                </details>
                <ReferenceContext key={source.id} source={source} onApplied={async id => {await refresh(); setSelected(old => [...new Set(old.map(selectedId => selectedId === source.id ? id : selectedId))]); chooseConversation(id); setNotice('Справочные материалы сохранены. Прежние результаты доступны в истории; для новой оценки запустите проверку.')}} onError={setError}/>
                {(source.metadata.recording_url || source.resolved_recording?.url) && <Recording key={source.metadata.recording_url || source.resolved_recording?.url} url={(source.metadata.recording_url || source.resolved_recording?.url)!}/>}
                {source.channel === 'voice call' && !(source.metadata.recording_url || source.resolved_recording?.url) && <p className={styles.muted}>Оценивается только расшифровка звонка. Без аудиозаписи нельзя оценить особенности речи.</p>}
                {focus.ids.length > 0 && <div className={styles.evidenceNavigation}><span>Выделена цитата из обоснования</span><button onClick={() => setDetailTab('review')}>К результату проверки</button></div>}
                {source.content.messages.map(m => {
                  const selected = (focus.items || []).filter(item => item.message_id === m.id)
                  const highlight = sourceHighlights(m.text, 'dialogue', m.id, selected)
                  return <article id={`message-${m.id}`} data-testid={`message-${m.id}`} tabIndex={-1} key={m.id} className={`${styles.message} ${styles[m.speaker] || ''} ${focus.ids.includes(m.id) ? styles.highlight : ''}`}>
                    <div><b>{m.speaker === 'operator' ? 'Оператор' : m.speaker === 'client' ? 'Клиент' : m.speaker === 'bot' ? 'Бот' : 'Система'}</b><span title={`Сообщение ${m.id}`}>{m.timestamp}</span></div><p><Highlighted text={m.text} ranges={highlight.ranges}/></p>
                    {highlight.invalid && <small role="status">Не удалось найти точное совпадение цитаты в сохранённом диалоге.</small>}
                  </article>
                })}
              </> : <p className={styles.empty}>Загрузка диалога…</p>}
            </section>
            <section aria-label="Результат проверки" hidden={detailTab === 'transcript'} className={styles.results}>
              {detailTab === 'split' && <h3 className={styles.paneTitle}>Результат проверки</h3>}
              {jobs.length > 0 && <details className={styles.savedReviews}><summary>Сохранённые результаты <span>{jobs.length}</span></summary>
                <label>Дата проверки<select aria-label="Сохранённая оценка" value={jobId} onChange={e => setJobId(e.target.value)}><option value="">Выберите результат проверки</option>{jobs.map(j => <option key={j.id} value={j.id}>{date(j.created_at)} · {reviewStatus(j.status, j.is_demo)} · {j.id.slice(0, 7)}</option>)}</select></label>
                {job && <><p>Чек-лист: {job.checklist.title} · {job.checklist.version}</p><AssessmentComparison key={job.id} job={job} jobs={jobs}/></>}
              </details>}
              {job ? <Assessment key={job.id} job={job} busy={busy} onRetry={() => setRetryReview(true)} onCancel={() => act(async () => {await api(`/jobs/${job.id}/cancel`, {}); await refreshJob()})} onEvidence={evidence} onReference={(ref, quote, selection) => setReference({ref, quote, selection})} onAppeal={setAppealCriterion} onResolve={setResolveAppeal}/> : <div className={styles.empty}><div className={styles.emptyIcon}><Icon name="list" size={25}/></div><h2>{jobId ? 'Загрузка результата…' : 'Диалог ещё не проверен'}</h2><p>{jobId ? 'Здесь появится сохранённый результат.' : 'Нажмите «Начать проверку» вверху диалога, чтобы получить оценку по выбранным критериям.'}</p></div>}
            </section>
            </div>
          </> : <div className={styles.welcome}><div className={styles.emptyIcon}><Icon name="chat" size={26}/></div><h2>Посмотрите, как работает проверка</h2><p>Откройте пример, изучите обоснование оценки, затем загрузите свои диалоги.</p><div className={styles.welcomeSteps}><button disabled={busy} onClick={tryExample}><Icon name="play" size={18}/><span><b>Открыть пример</b>Готовый разбор без ключа и оплаты</span><Icon name="arrow" size={16}/></button><button onClick={() => setShowImport(true)}><Icon name="upload" size={18}/><span><b>Загрузить данные</b>Чаты и расшифровки звонков</span><Icon name="arrow" size={16}/></button></div><button className={styles.welcomeHelp} onClick={() => setShowSetup(true)}>Инструкция по настройке и проверке</button></div>}
        </div>
      </main></>}
    {showImport && <Modal title="Загрузить данные" onClose={() => setShowImport(false)}>
      <div className={styles.importModes} aria-label="Способ загрузки"><button aria-pressed={importMode === 'text'} onClick={() => setImportMode('text')}>Вставить текст</button><button aria-pressed={importMode === 'file'} onClick={() => setImportMode('file')}>Загрузить файл</button></div>
      {importMode === 'text' ? <TextImport busy={busy} onImport={importNow} onClose={() => setShowImport(false)}/> : <>
      <p>Загрузите чаты или расшифровки звонков в формате JSON или JSONL. Прежние данные и оценки сохранятся.</p>
      <p><a download="judge-example.json" href={`data:application/json;charset=utf-8,${encodeURIComponent(exampleText)}`}>Скачать образец файла</a> — он показывает нужный формат. Поддерживаются также файлы организаторов со структурой <code>data.records</code>. Файлы CSV и аудиозаписи не поддерживаются.</p>
      <p>Загрузка бесплатна. Будет выбран только первый диалог; проверку вы запускаете отдельно.</p>
      <label className={styles.fileUpload}><Icon name="upload" size={24}/><span>Выбрать файл</span><input aria-label="Файл с диалогами" type="file" accept=".json,.jsonl,application/json" onChange={e => {const file = e.target.files?.[0]; if (file) file.text().then(text => {setImportText(text); setImportFileName(file.name)}).catch(e => setError(e.message))}}/></label>
      {importFileName && <p className={styles.fileReady}><Icon name="check" size={16}/>{importFileName} готов к загрузке</p>}
      <details open={!!importText && !importFileName}><summary>Или вставьте JSON</summary><textarea aria-label="Диалоги в формате JSON" rows={8} value={importText} onChange={e => {setImportText(e.target.value); setImportFileName('')}} placeholder="Вставьте JSON или JSONL"/></details>
      {error && <p role="alert" className={styles.error}>{error}</p>}
      <div className={styles.dialogFooter}><button onClick={() => setShowImport(false)}>Отмена</button><button className={styles.primary} disabled={busy || !importText.trim()} onClick={() => importNow()}>{busy ? 'Загрузка…' : 'Загрузить'}</button></div></>}
      {importMode === 'text' && error && <p role="alert" className={styles.error}>{error}</p>}
    </Modal>}
    {!showSetup && (runIds.length > 0 || retryReview) && <Modal title={retryReview ? 'Повторить проверку' : runIds.length === 1 ? 'Начать проверку' : `Проверка диалогов: ${runIds.length}`} onClose={() => {setRunIds([]); setRetryReview(false)}}>
      <p>Выберите параметры проверки {runIds.length > 1 ? 'выбранных диалогов' : 'диалога'}.</p>
      {!retryReview && runIds.length === 1 && runIds[0] === exampleId && <p className={styles.exampleHint}><b>Учебный пример · 9 сообщений</b><br/>Вы уже смотрели готовый учебный разбор. Здесь запускается отдельная оценка моделью по выбранному чек-листу — с API-ключом и возможными расходами.</p>}
      {!retryReview && runIds.length > 1 && <p>Указанный лимит расходов общий для всех выбранных диалогов ({runIds.length}). <button className={styles.quiet} onClick={() => {setSelected([runIds[0]]); setRunIds([runIds[0]])}}>Сначала проверить один</button></p>}
      {retryReview ? <p>Исходный чек-лист: <b>{job?.checklist.title}</b></p> : <label>Чек-лист<select aria-label="Чек-лист для проверки" value={checklistId} onChange={e => setChecklistId(e.target.value)}>{availableChecklists.map(c => <option key={c.id} value={c.id}>{c.title}{c.external_id === config?.default_checklist.id ? ' (основной)' : ''}</option>)}</select></label>}
      <details className={styles.reviewOptions} open={retryReview || undefined}><summary>Параметры проверки</summary>
        {!retryReview && <><label>Режим проверки<select aria-label="Режим проверки" value={strategy} onChange={e => setStrategy(e.target.value as 'assessor'|'assessor-reviewed')}><option value="assessor">Обычная проверка</option><option value="assessor-reviewed">С независимой перепроверкой</option></select></label>
        <p>{strategy === 'assessor-reviewed' ? 'Независимая перепроверка помогает выявить спорные выводы, но увеличивает расходы. Некоторые вопросы всё равно могут потребовать вашего решения.' : 'Диалог проверяется по всем критериям выбранного чек-листа. Выводы сопровождаются цитатами из диалога.'}</p></>}
        <label>Лимит расходов, USD<input aria-label="Лимит расходов на проверку" type="number" min="0.01" step="0.01" value={budget} onChange={e => setBudget(e.target.value)}/></label>
        {config && <p>Из общего лимита {dollars(config.ledger.lifetime_limit_usd)} использовано {dollars(config.ledger.lifetime_committed_usd)}.</p>}
      </details>
      <p className={styles.costSummary}>{retryReview ? 'Повторная платная проверка' : strategy === 'assessor-reviewed' ? 'Независимая перепроверка' : 'Обычная проверка'} · Лимит расходов: <b>{new Intl.NumberFormat('ru-RU', {style: 'currency', currency: 'USD'}).format(Number(budget) || 0)}</b><br/><span>{retryReview ? 'Предыдущий результат сохранится. Будут использованы прежние критерии и режим проверки.' : 'Совпадающие сохранённые результаты используются без дополнительной оплаты.'}</span></p>
      <p className={styles.muted}>Проверка короткого диалога обычно занимает несколько десятков секунд. Длинные диалоги требуют больше времени.</p>
      {savedReview && <p className={styles.savedReviewLink}>По этому чек-листу уже есть результат от {date(savedReview.created_at)}. <button onClick={() => {setRunIds([]); chooseJob(savedReview)}}>Открыть сохранённый результат</button><small>Бесплатный просмотр с исходными параметрами и выводами.</small></p>}
      {!reviewReady && <div className={styles.warning}>{!config ? 'Не удалось проверить настройки.' : !config.api_key_configured ? 'Перед проверкой укажите API-ключ в настройках сервера.' : 'Достигнут установленный лимит расходов.'} <button onClick={() => setShowSetup(true)}>Открыть инструкцию</button></div>}
      {error && <p role="alert" className={styles.error}>{error}</p>}
      <div className={styles.dialogFooter}><button onClick={() => {setRunIds([]); setRetryReview(false)}}>Отмена</button><button className={styles.primary} disabled={busy || !reviewReady || (!retryReview && !checklistId) || !Number.isFinite(Number(budget)) || Number(budget) < 0.01} onClick={() => retryReview ? retry() : run(runIds)}>{busy ? 'Запуск…' : 'Начать проверку'}</button></div>
    </Modal>}
    {showSetup && <SetupHelp config={config} onClose={() => setShowSetup(false)} onRefresh={async () => {try {setConfig(await api<Config>('/config'))} catch (e) {setConfig(undefined); throw e}}} onExample={tryExample} onUpload={() => {setShowSetup(false); setRunIds([]); setRetryReview(false); setShowImport(true)}} onChecklist={addChecklist}/>}
    {reference && <div className={styles.overlay}><section className={styles.dialog}><button className={styles.close} onClick={() => setReference(undefined)}>Закрыть материал</button><h2>{referenceTitle(reference.ref, source?.metadata)}</h2><p>{reference.ref.provenance}</p>
      <p>Область применения: {reference.ref.scope || 'Сведения из приложенного материала'} · {referenceDate(reference.ref)}</p>
      {safeLink(reference.ref.source_url) && <a href={safeLink(reference.ref.source_url)} target="_blank" rel="noreferrer">Первоисточник</a>}
      <p className={styles.sourceText}>{referenceHighlight ? <Highlighted text={reference.ref.text} ranges={referenceHighlight.ranges}/> : reference.ref.text}</p>
      {referenceHighlight?.invalid && <p role="status">Цитата не совпадает с сохранённым источником. Точная подсветка недоступна.</p>}
    </section></div>}
    {appealCriterion && job && <AppealForm job={job} criterionId={appealCriterion} onClose={() => setAppealCriterion(undefined)} onSaved={async () => {await Promise.all([refreshJob(), refresh()]); setAppealCriterion(undefined)}} onError={setError}/>}
    {resolveAppeal && job && <ResolveForm key={`${job.id}-${resolveAppeal.id}`} job={job} appeal={resolveAppeal} onClose={() => setResolveAppeal(undefined)} onSaved={async () => {await Promise.all([refreshJob(), refresh()]); setResolveAppeal(undefined)}} onError={setError}/>}
  </div>
}

function History({onSelect}: {onSelect: (j: JobRow) => void}) {
  const [jobs, setJobs] = useState<JobRow[]>([]), [error, setError] = useState('')
  const [sources, setSources] = useState<ConversationRow[]>([]), [lists, setLists] = useState<ChecklistRow[]>([])
  useEffect(() => {Promise.all([api<JobRow[]>('/jobs'), api<ConversationRow[]>('/conversations'), api<ChecklistRow[]>('/checklists')])
    .then(([savedJobs, conversations, checklists]) => {setJobs(savedJobs); setSources(conversations); setLists(checklists)}).catch(e => setError(e.message))}, [])
  return <section className={styles.page}><h1>История оценок</h1>{error && <p role="alert">{error}</p>}<p>Откройте результат, чтобы увидеть оценку, использованный чек-лист и решения по пересмотру.</p>
    <table><thead><tr><th>Дата</th><th>Диалог</th><th>Чек-лист</th><th>Статус</th><th></th></tr></thead><tbody>{jobs.map(j => <tr key={j.id}><td>{date(j.created_at)}</td><td>{sources.find(c => c.id === j.conversation_id)?.display_title || 'Сохранённый диалог'}</td><td>{lists.find(c => c.id === j.checklist_id)?.title || 'Сохранённый чек-лист'}</td><td><span className={styles.status} data-status={j.status}>{reviewStatus(j.status, j.is_demo)}</span>{j.review_revision > 0 && <small className={styles.humanReview}>Результат пересмотрен</small>}</td><td><button onClick={() => onSelect(j)}>Открыть результат</button></td></tr>)}</tbody></table>{!jobs.length && <p>Проверок пока нет. Загрузите диалоги и выберите чек-лист, чтобы начать.</p>}</section>
}
export default App
