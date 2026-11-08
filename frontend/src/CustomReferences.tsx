import {useEffect, useId, useRef, useState} from 'react'
import type {ConversationDetail} from './types'
import {referenceReason} from './format'
import {customReferenceRequest, customReferenceWarning, type CustomReferenceDraft, type CustomReferenceSaved, type CustomReferenceSummary} from './CustomReferenceApi'
import appStyles from './App.module.css'
import styles from './CustomReferences.module.css'

type Draft = CustomReferenceDraft & {key: string}
const newDraft = (): Draft => ({key: crypto.randomUUID(), title: '', text: '', source_url: '', source_note: '', scope: '',
  date_kind: 'unknown', snapshot_on: '', valid_from: '', valid_until: ''})

export function CustomReferences({source, onApplied, onError}: {
  source: ConversationDetail; onApplied: (id: string) => Promise<void>; onError: (message: string) => void
}) {
  const [editing, setEditing] = useState(false), [drafts, setDrafts] = useState<Draft[]>(() => [newDraft()])
  const [busy, setBusy] = useState(false), [reading, setReading] = useState(false), [error, setError] = useState('')
  const [preview, setPreview] = useState<{key: string; summary: CustomReferenceSummary}>()
  const form = useRef<HTMLFormElement>(null), fileRequest = useRef(0), active = useRef(true)
  const formId = useId()
  useEffect(() => {active.current = true; return () => {active.current = false}}, [])
  const documents = drafts.map(({key: _key, ...document}) => document)
  const key = JSON.stringify(documents)
  const shownPreview = preview?.key === key ? preview.summary : undefined
  const knownScope = source.content.knowledge_scope || source.content.reference_context?.scope || ''
  function change(id: string, patch: Partial<CustomReferenceDraft>) {
    setDrafts(old => old.map(draft => draft.key === id ? {...draft, ...patch} : draft)); setError('')
  }
  function fail(message: string) {setError(message); onError(message)}
  async function loadFiles(files: File[]) {
    const request = ++fileRequest.current
    setError(''); setReading(true)
    try {
      if (files.length > 10) throw new Error('За один раз можно добавить не более 10 документов.')
      const retainedCount = drafts.length === 1 && !drafts[0].title.trim() && !drafts[0].text.trim() ? 0 : drafts.length
      if (retainedCount + files.length > 10) throw new Error('В форме уже есть документы. Всего можно прикрепить не более 10.')
      const loaded = await Promise.all(files.map(async file => {
        if (!/\.(txt|md)$/i.test(file.name)) throw new Error('Поддерживаются файлы TXT и MD. Из PDF или Word скопируйте нужный текст.')
        if (file.size > 1_000_000) throw new Error('Файл слишком большой. Выберите нужный фрагмент: до 100 000 символов на документ.')
        let text: string
        try {text = new TextDecoder('utf-8', {fatal: true}).decode(await file.arrayBuffer())}
        catch {throw new Error('Не удалось прочитать текст. Сохраните файл в кодировке UTF-8 и загрузите снова.')}
        if (!text.trim() || text.includes('\0')) throw new Error('В файле нет подходящего текста. Вставьте текст документа вручную.')
        if (text.length > 100_000) throw new Error('В документе больше 100 000 символов. Разделите его или выберите нужный фрагмент.')
        return {...newDraft(), title: file.name.replace(/\.(txt|md)$/i, '').slice(0, 200), text}
      }))
      if (request !== fileRequest.current || !active.current) return
      setDrafts(old => {
        const retained = old.length === 1 && !old[0].title.trim() && !old[0].text.trim() ? [] : old
        return [...retained, ...loaded]
      })
    } catch (problem) {if (request === fileRequest.current && active.current) fail((problem as Error).message)}
    finally {if (request === fileRequest.current && active.current) setReading(false)}
  }
  async function submit(previewOnly: boolean) {
    form.current?.querySelectorAll(':invalid').forEach(field => {
      for (let parent = field.parentElement; parent && parent !== form.current; parent = parent.parentElement) {
        if (parent instanceof HTMLDetailsElement) parent.open = true
      }
    })
    if (!form.current?.reportValidity()) return
    if (documents.some(item => item.date_kind === 'validity' && !item.valid_from && !item.valid_until)) {
      fail('Для периода действия укажите хотя бы начальную или конечную дату.'); return
    }
    if (documents.reduce((sum, item) => sum + item.text.length, 0) > 300_000) {
      fail('За один раз можно прикрепить до 300 000 символов. Разделите документы на несколько загрузок.'); return
    }
    setBusy(true); setError('')
    try {
      if (previewOnly) {
        const summary = await customReferenceRequest<CustomReferenceSummary>(source.id, documents, true)
        if (active.current) setPreview({key, summary})
      }
      else {
        const saved = await customReferenceRequest<CustomReferenceSaved>(source.id, documents)
        if (!active.current) return
        await onApplied(saved.id)
        if (active.current) {setEditing(false); setDrafts([newDraft()]); setPreview(undefined)}
      }
    } catch (problem) {if (active.current) fail((problem as Error).message)} finally {if (active.current) setBusy(false)}
  }
  return <div className={styles.custom}>
    <div className={styles.entry}>
      <div><h3>Справочные документы</h3><p>Прикреплено: {source.reference_count}</p></div>
      <button type="button" disabled={busy} aria-expanded={editing} aria-controls={formId}
        onClick={() => {++fileRequest.current; setReading(false); setEditing(!editing); setError('')}}>{editing ? 'Свернуть форму' : 'Добавить свой документ'}</button>
    </div>
    {editing && <form ref={form} id={formId} className={styles.editor} onSubmit={event => {event.preventDefault(); void submit(false)}}>
        <div className={styles.heading}><h4>Добавление документов</h4></div>
        <p>Вставьте текст или загрузите TXT/MD в кодировке UTF-8. Из PDF или Word скопируйте нужный текст. До 10 документов, не более 100 000 символов в каждом.</p>
        <label className={styles.upload}>Загрузить TXT или MD<input type="file" accept=".txt,.md,text/plain,text/markdown" multiple disabled={busy || reading} onChange={event => {const files = Array.from(event.target.files || []); event.target.value = ''; if (files.length) void loadFiles(files)}}/></label>
        {reading && <p role="status">Читаем файлы…</p>}
        {drafts.map((draft, index) => <fieldset key={draft.key} disabled={busy || reading} className={styles.document}>
          <legend>Документ {index + 1}</legend>
          <label>Название документа<input required maxLength={200} value={draft.title} onChange={event => change(draft.key, {title: event.target.value})} placeholder="Например, Как изменить адрес доставки"/></label>
          <label>Текст документа<textarea required maxLength={100_000} rows={6} value={draft.text} onChange={event => change(draft.key, {text: event.target.value})} placeholder="Вставьте исходный текст без пересказа"/></label>
          <p className={styles.count}>{new Intl.NumberFormat('ru-RU').format(draft.text.length)} из 100 000 символов</p>
          <details className={styles.optional}><summary>Источник, тема и даты <span>необязательно</span></summary>
            <p>Заполните только то, что известно. Эти сведения не меняют дату и продукт исходного диалога.</p>
            <label>Ссылка на источник<input type="url" pattern="https?://.+" maxLength={2048} value={draft.source_url} onChange={event => change(draft.key, {source_url: event.target.value})} placeholder="https://…"/><small>Ссылка сохраняется для проверки вручную. Приложение не загружает её содержимое.</small></label>
            <label>Откуда документ?<input maxLength={1000} value={draft.source_note} onChange={event => change(draft.key, {source_note: event.target.value})} placeholder="Например, внутренняя инструкция отдела поддержки"/></label>
            <label>Продукт или тема документа<input maxLength={200} value={draft.scope} onChange={event => change(draft.key, {scope: event.target.value})} placeholder="Оставьте пустым, если неизвестно"/></label>
            {knownScope && knownScope.length <= 200 && <button type="button" className={styles.copyScope} onClick={() => change(draft.key, {scope: knownScope})}>Использовать тему диалога: {knownScope}</button>}
            <label>Что известно о дате документа?<select value={draft.date_kind} onChange={event => change(draft.key, {date_kind: event.target.value as Draft['date_kind'], snapshot_on: '', valid_from: '', valid_until: ''})}>
              <option value="unknown">Дата не указана</option><option value="snapshot">Сведения сохранены на конкретную дату</option><option value="validity">Известен период действия</option>
            </select></label>
            {draft.date_kind === 'snapshot' && <label>На какую дату сохранены сведения?<input type="date" required value={draft.snapshot_on} onChange={event => change(draft.key, {snapshot_on: event.target.value})}/><small>Это дата снимка документа, а не начало действия правил.</small></label>}
            {draft.date_kind === 'validity' && <div className={styles.dates}><label>Действует с<input type="date" value={draft.valid_from} onChange={event => change(draft.key, {valid_from: event.target.value})}/></label><label>Действует до<input type="date" value={draft.valid_until} onChange={event => change(draft.key, {valid_until: event.target.value})}/></label></div>}
          </details>
          {drafts.length > 1 && <button type="button" className={styles.remove} onClick={() => setDrafts(old => old.filter(item => item.key !== draft.key))}>Удалить документ {index + 1}</button>}
        </fieldset>)}
        <button type="button" disabled={drafts.length >= 10 || busy || reading} onClick={() => setDrafts(old => [...old, newDraft()])}>Добавить ещё документ</button>
        <p className={styles.qualification}>Подлинность документа не проверяется. Если дата или продукт неизвестны, применимость останется неподтверждённой.</p>
        {shownPreview && <section className={styles.preview} aria-label="Применимость ваших документов"><h4>Перед сохранением</h4>{shownPreview.documents.map(document => <div key={document.id}>
          <b>{document.title}</b><p>{document.usable ? 'По указанным условиям документ можно передать на проверку. Это не подтверждение достоверности.' : `Документ сохранится, но не будет использован: ${document.rejection_reasons.map(referenceReason).join('; ')}.`}</p>
          {document.warnings.filter(warning => warning !== 'user_provided').map(warning => <p className={styles.warning} key={warning}>{customReferenceWarning(warning)}</p>)}
        </div>)}</section>}
        {error && <p className={styles.error} role="alert">{error}</p>}
        <p className={styles.savedHint}>Сохранится новая версия диалога со всеми прежними документами. Старые оценки останутся без изменений. Добавление документов не запускает платную проверку.</p>
        <div className={styles.actions}><button type="button" disabled={busy || reading} onClick={() => void submit(true)}>Проверить применимость</button><button type="submit" className={appStyles.primary} disabled={busy || reading}>{busy ? 'Сохраняем…' : 'Прикрепить документы'}</button></div>
      </form>}
  </div>
}
