import {useEffect, useState} from 'react'
import type {ConversationDetail, EvidenceContext, ReferenceMode, ReferencePack} from './types'
import {api} from './api'
import {dateOrigin, referenceDate, referenceReason, safeLink} from './format'
import styles from './App.module.css'
import {CustomReferences} from './CustomReferences'
import {customReferenceMetadata, customReferenceWarning, referenceTitle} from './CustomReferenceApi'
import customStyles from './CustomReferences.module.css'

type Selection = {pack_id: string; scope: string; mode: ReferenceMode; occurred_on: string|null;
  as_of: string|null; rationale: string}

export function ReferenceContext({source, onApplied, onError}: {
  source: ConversationDetail; onApplied: (id: string) => Promise<void>; onError: (s: string) => void
}) {
  const [packs, setPacks] = useState<ReferencePack[]>([]), [context, setContext] = useState<EvidenceContext>()
  const [selected, setSelected] = useState(''), [mode, setMode] = useState<ReferenceMode>('conversation_date')
  const [occurredOn, setOccurredOn] = useState(source.content.occurred_on || ''), [asOf, setAsOf] = useState('')
  const [rationale, setRationale] = useState(''), [scopeConfirmed, setScopeConfirmed] = useState(false)
  const [pending, setPending] = useState(false), [error, setError] = useState('')
  const [preview, setPreview] = useState<{key: string; context: EvidenceContext}>()
  useEffect(() => {
    let cancelled = false
    Promise.all([api<ReferencePack[]>('/reference-packs'), api<EvidenceContext>(`/conversations/${source.id}/evidence-context`)])
      .then(([available, saved]) => {if (!cancelled) {setPacks(available); setContext(saved); setOccurredOn(saved.temporal.occurred_on || '')}})
      .catch(e => {if (!cancelled) {setError(e.message); onError(e.message)}})
    return () => {cancelled = true}
  }, [source.id, onError])
  const pack = packs.find(p => p.id === selected)
  const snapshotDates = [...new Set(pack?.references.map(r => r.snapshot_on).filter((on): on is string => !!on) || [])].sort()
  const selection: Selection = {pack_id: selected, scope: pack?.scope || '', mode,
    occurred_on: mode === 'conversation_date' ? occurredOn || null : null,
    as_of: mode === 'snapshot_review' ? asOf || null : null, rationale: rationale.trim()}
  const key = JSON.stringify(selection)
  const currentPreview = preview?.key === key ? preview.context : undefined
  const previewRefs = currentPreview?.references.filter(r => pack?.references.some(ref => ref.id === r.reference_id)) || []
  const validSelection = !!(pack && scopeConfirmed && selection.rationale &&
    (mode === 'conversation_date' ? occurredOn : asOf) && !context?.temporal.has_conflict)
  const usable = previewRefs.filter(r => r.usable).length
  const customDocuments = customReferenceMetadata(source)
  async function previewSelection() {
    setPending(true); setError(''); setPreview(undefined)
    try {setPreview({key, context: await api<EvidenceContext>(`/conversations/${source.id}/references/preview`, selection)})}
    catch (e) {setError((e as Error).message); onError((e as Error).message)} finally {setPending(false)}
  }
  return <section className={styles.context} aria-label="Справочные документы">
    <CustomReferences source={source} onApplied={onApplied} onError={onError}/>
    <details className={customStyles.contextInfo}>
    <summary>Документы и условия проверки</summary>
    <details className={customStyles.dialogueContext}><summary>Дата и тема диалога</summary>
    <p>Дата диалога: <b>{context?.temporal.occurred_on || source.content.occurred_on || 'не указана'}</b>
      {context && <> · Источник даты: {dateOrigin(context.temporal.origin)}</>}</p>
    <p>Продукт или услуга: {source.content.knowledge_scope || 'не указаны'}</p>
    </details>
    {context?.temporal.has_conflict && <p role="alert" className={styles.error}>В датах есть противоречие: {referenceReason(context.temporal.conflict_reason || "source_date_conflict")}. Исправьте исходные данные, прежде чем выбирать документы.</p>}
    {context?.assessment.conditional && <div className={styles.warning}><b>Проверка с допущением о дате и продукте</b>
      <p>Принятый продукт: {context.assessment.scope} · Сведения на {context.assessment.as_of}. Дата и продукт в исходном диалоге не меняются.</p>
      <p>{context.assessment.rationale}</p></div>}
    {!!source.content.references.length && <div className={customStyles.sourceList}>
      {source.content.references.map(reference => {
        const custom = customDocuments[reference.id]
        const applicability = context?.references.find(item => item.reference_id === reference.id)
        const missingScope = custom && !custom.scope
        const missingDate = custom?.date_kind === 'unknown'
        const clarification = missingScope && missingDate
          ? 'Не указаны тема и дата документа. Уточните, относится ли он к этому диалогу и действовал ли на его дату.'
          : missingScope ? 'Тема документа не указана. Уточните, относится ли он к этому диалогу.'
            : missingDate ? 'Дата документа не указана. Уточните, действовал ли он на дату диалога.' : ''
        const shortDate = reference.snapshot_on ? `сведения на ${reference.snapshot_on}`
          : reference.valid_from || reference.valid_until ? `действует ${reference.valid_from ? `с ${reference.valid_from}` : ''}${reference.valid_until ? ` до ${reference.valid_until}` : ''}`.trim()
            : 'дата не указана'
        return <article className={customStyles.source} key={reference.id}>
          <b>{referenceTitle(reference, source.metadata)}</b>
          <p>{custom ? 'Документ пользователя' : 'Прикреплённый источник'} · {reference.scope || 'тема не указана'} · {shortDate}</p>
          {applicability && <p className={!applicability.usable || clarification ? customStyles.warning : undefined}>{applicability.usable
            ? clarification || 'Доступен для проверки.'
            : `Не используется: ${referenceReason(applicability.rejection_reasons[0] || '')}.`}</p>}
          <details><summary>Текст документа</summary><pre>{reference.text}</pre></details>
          <details><summary>Сведения об источнике</summary>
            <p>{reference.provenance}</p>
            <p>Продукт или тема: {reference.scope || 'не указаны'} · {reference.snapshot_on || reference.valid_from || reference.valid_until ? referenceDate(reference) : 'Дата актуальности не указана'}</p>
            {safeLink(reference.source_url) && <a href={safeLink(reference.source_url)} target="_blank" rel="noreferrer">Открыть источник</a>}
            {custom && (!custom.scope || custom.date_kind === 'unknown') && <p className={customStyles.warning}>{!custom.scope ? customReferenceWarning('scope_unknown') : ''} {custom.date_kind === 'unknown' ? customReferenceWarning('date_unknown') : ''}</p>}
            {applicability && !applicability.usable && <p className={customStyles.warning}>Причины исключения: {applicability.rejection_reasons.map(referenceReason).join('; ')}.</p>}
          </details>
        </article>
      })}</div>}
    <details className={customStyles.packOptions}><summary>Выбрать готовый набор документов</summary>
    <p>Выберите условия проверки и посмотрите, какие документы им соответствуют. При добавлении документов создаётся новая версия диалога. Прежние оценки остаются без изменений.</p>
    {error && <p role="alert" className={styles.error}>{error}</p>}
    <label>Набор документов<select aria-label="Набор документов" value={selected} onChange={e => {
      const next = packs.find(p => p.id === e.target.value)
      setSelected(e.target.value); setScopeConfirmed(false); setError(''); setPreview(undefined)
      const dates = [...new Set(next?.references.map(r => r.snapshot_on).filter((on): on is string => !!on) || [])]
      setAsOf(dates.length === 1 ? dates[0] : '')
    }}><option value="">Выберите набор документов</option>{packs.map(p => <option key={p.id} value={p.id}>{p.title || p.id} · {p.scope}</option>)}</select></label>
    <label>Условия проверки<select aria-label="Условия проверки документов" value={mode} onChange={e => {setMode(e.target.value as ReferenceMode); setScopeConfirmed(false); setError(''); setPreview(undefined)}}>
      <option value="conversation_date">Использовать фактическую дату диалога</option>
      <option value="snapshot_review">Использовать документы на выбранную дату</option>
    </select></label>
    {mode === 'conversation_date' ? <label>Дата диалога<input aria-label="Дата диалога" type="date" value={occurredOn}
      disabled={!!context?.temporal.occurred_on} onChange={e => {setOccurredOn(e.target.value); setError('')}}/></label> : <>
      <p className={styles.warning}>Выбранные продукт и дата будут приняты как допущение. Это не подтверждает, что диалог относился к этому продукту и правила действовали в тот момент.</p>
      <label>Дата, на которую сохранены документы<input aria-label="Дата, на которую сохранены документы" type="date" value={asOf} onChange={e => {setAsOf(e.target.value); setError('')}}/></label>
      {snapshotDates.length > 0 && <p>Доступны документы на даты: {snapshotDates.join(', ')}. Это даты сохранения источников, а не вступления правил в силу.</p>}
    </>}
    {pack && <label><input aria-label="Подтвердить применимость продукта" type="checkbox" checked={scopeConfirmed} onChange={e => setScopeConfirmed(e.target.checked)}/>
      {mode === 'conversation_date' ? `Диалог относится к продукту: ${pack.scope}.` : `Для этой проверки принять продукт «${pack.scope}» как допущение.`}</label>}
    <label>{mode === 'conversation_date' ? 'Чем подтверждены продукт и дата диалога?' : 'Почему выбраны эти продукт и дата?'}
      <textarea aria-label="Обоснование выбора документов" rows={3} value={rationale} onChange={e => {setRationale(e.target.value); setError('')}}/></label>
    <div className={styles.row}>
      <button disabled={!validSelection || pending} onClick={previewSelection}>Проверить применимость</button>
      <button disabled={!validSelection || pending || !currentPreview || !usable} onClick={async () => {
        setPending(true); setError('')
        try {const value = await api<ConversationDetail>(`/conversations/${source.id}/references`, selection); await onApplied(value.id)}
        catch (e) {setError((e as Error).message); onError((e as Error).message)} finally {setPending(false)}
      }}>Сохранить новую версию</button>
    </div>
    {currentPreview && <div role="status"><b>Подходит документов: {usable} из {previewRefs.length}</b>
      {currentPreview.assessment.conditional && <p className={styles.warning}>Результат будет основан на допущении: {currentPreview.assessment.scope}, сведения на {currentPreview.assessment.as_of}.</p>}
      {previewRefs.map(r => <p key={r.reference_id}>{r.reference_id}: {r.usable ? 'Подходит' : `Не подходит: ${r.rejection_reasons.map(referenceReason).join('; ')}`}</p>)}
      {!usable && <p>Эти документы не подходят для выбранных условий. Уточните условия или выберите другие документы. Не меняйте дату диалога, чтобы подогнать её под источник.</p>}
    </div>}
    {pack && <details><summary>Сведения об источниках и ограничения</summary>{pack.usage_notes?.map((n, i) => <p key={i}>{n}</p>)}
      {pack.references.map(r => <p key={r.id}>{r.id} · {referenceDate(r)} · {safeLink(r.source_url) && <a href={safeLink(r.source_url)} target="_blank" rel="noreferrer">Открыть источник</a>}</p>)}
    </details>}
    </details>
    </details>
  </section>
}
