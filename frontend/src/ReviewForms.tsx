import {useEffect, useState} from 'react'
import type {Appeal, JobDetail, Judgment, ReferenceOption} from './types'
import {api} from './api'
import {referenceDate, referenceReason} from './format'
import styles from './App.module.css'

type Shared = {job: JobDetail; onClose: () => void; onSaved: () => Promise<void>; onError: (s: string) => void}
const speakerName = (speaker: string) => speaker === 'operator' ? 'Оператор' : speaker === 'client' ? 'Клиент' : speaker === 'bot' ? 'Бот' : speaker === 'system' ? 'Система' : speaker
export function AppealForm({job, criterionId, onClose, onSaved, onError}: Shared & {criterionId: string}) {
  const [author, setAuthor] = useState(''), [reason, setReason] = useState(''), [ids, setIds] = useState<string[]>([]), [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const criterionTitle = job.checklist.content.criteria.find(c => c.id === criterionId)?.title || 'Критерий оценки'
  return <div className={styles.overlay}><form className={styles.dialog} role="dialog" aria-modal="true" aria-label="Запросить пересмотр" onSubmit={async e => {e.preventDefault(); setPending(true); try {
    await api(`/jobs/${job.id}/appeals`, {criterion_id: criterionId, author, reason, message_ids: ids}); await onSaved()
  } catch (e) {setError((e as Error).message); onError((e as Error).message)} finally {setPending(false)} }}>
    <button type="button" className={styles.close} onClick={onClose}>Закрыть</button><h2>Запросить пересмотр</h2><p><b>{criterionTitle}</b></p>
    {error && <p role="alert" className={styles.error}>{error}</p>}
    <label>Ваше имя<input aria-label="Имя автора запроса" required value={author} onChange={e => setAuthor(e.target.value)}/></label>
    <label>Что нужно пересмотреть?<textarea aria-label="Причина пересмотра" required value={reason} onChange={e => setReason(e.target.value)}/></label>
    <p>Выберите сообщения, на которые вы ссылаетесь:</p><div className={styles.messagePicker}>{job.conversation.content.messages.map(m => <label key={m.id}><input type="checkbox" aria-label={`${m.id} · ${speakerName(m.speaker)}: ${m.text}`} checked={ids.includes(m.id)} onChange={e => setIds(old => e.target.checked ? [...old, m.id] : old.filter(id => id !== m.id))}/>{speakerName(m.speaker)} · {m.timestamp}: {m.text}</label>)}</div>
    <button type="submit" className={styles.primary} disabled={!ids.length || pending}>Отправить запрос</button>
  </form></div>
}

export function ResolveForm({job, appeal, onClose, onSaved, onError}: Shared & {appeal: Appeal}) {
  const current = job.effective!.judgments.find(j => j.criterion_id === appeal.criterion_id)!
  const criterion = job.checklist.content.criteria.find(c => c.id === appeal.criterion_id)!
  const [decision, setDecision] = useState('reject'), [reviewer, setReviewer] = useState(''), [rationale, setRationale] = useState('')
  const [status, setStatus] = useState<Judgment['status']>(current.status), [answer, setAnswer] = useState(current.answer || criterion.levels[0].value)
  const [pending, setPending] = useState(false), [confirmed, setConfirmed] = useState(false)
  const [uncertainty, setUncertainty] = useState(current.uncertainty || '')
  const [clearUncertainty, setClearUncertainty] = useState(false), [uncertaintyResolution, setUncertaintyResolution] = useState('')
  const [error, setError] = useState('')
  const [references, setReferences] = useState<ReferenceOption[]>([]), [selectedReferences, setSelectedReferences] = useState<string[]>([])
  const [loadingSources, setLoadingSources] = useState(true)
  const [messageUses, setMessageUses] = useState<Record<string, 'support'|'counter'>>({})
  const [checkOmission, setCheckOmission] = useState(false)
  const [omissionStart, setOmissionStart] = useState(''), [omissionEnd, setOmissionEnd] = useState('')
  const messages = job.conversation.content.messages
  const startIndex = messages.findIndex(m => m.id === omissionStart), endIndex = messages.findIndex(m => m.id === omissionEnd)
  const validInterval = checkOmission && startIndex >= 0 && endIndex >= startIndex
  const selectedEvidence = messages.filter(m => messageUses[m.id] === 'support').map(m => ({message_id: m.id, quote: m.text}))
  const selectedCounterevidence = messages.filter(m => messageUses[m.id] === 'counter').map(m => ({message_id: m.id, quote: m.text}))
  const checkedIds = validInterval ? messages.slice(startIndex, endIndex + 1).map(m => m.id) : []
  const hasDecisionEvidence = (selectedEvidence.length > 0 || validInterval) && (!checkOmission || validInterval)
  const hadUncertainty = !!current.uncertainty?.trim()
  const clearsUncertainty = hadUncertainty && clearUncertainty && status !== 'needs_review'
  const validUncertainty = clearsUncertainty ? !!uncertaintyResolution.trim() : !hadUncertainty || !!uncertainty.trim()
  useEffect(() => {
    let cancelled = false
    api<{references: ReferenceOption[]}>(`/jobs/${job.id}/reference-options`).then(result => {
      if (!cancelled) {setReferences(result.references); setSelectedReferences([]); setLoadingSources(false)}
    }).catch(e => {if (!cancelled) {setError(e.message); onError(e.message); setLoadingSources(false)}})
    return () => {cancelled = true}
  }, [job.id, onError])
  return <div className={styles.overlay}><form className={styles.dialog} role="dialog" aria-modal="true" aria-label="Запрос на пересмотр" onSubmit={async e => {e.preventDefault(); if (decision === 'accept' && !hasDecisionEvidence) {setError('Выберите подтверждающие сообщения или укажите фрагмент диалога, в котором должно было прозвучать недостающее действие.'); return} if (decision === 'accept' && !validUncertainty) {setError('Сохраните замечание о недостающих сведениях либо подтвердите, что проверили их, и объясните результат.'); return} setPending(true); try {
    const decisionRationale = decision === 'accept' && clearsUncertainty
      ? `${rationale.trim()}\n\nНедостающие сведения проверены: ${uncertaintyResolution.trim()}` : rationale
    const replacement: Judgment = {criterion_id: appeal.criterion_id, status, answer: status === 'scored' ? answer : null,
      explanation: decisionRationale, evidence: selectedEvidence, counterevidence: selectedCounterevidence,
      checked_message_ids: checkedIds, uncertainty: clearsUncertainty ? null : uncertainty.trim() || (status === 'needs_review' ? rationale : null)}
    await api(`/appeals/${appeal.id}/resolve`, {decision, reviewer, rationale: decisionRationale, expected_revision: job.review_revision, judgment: decision === 'accept' ? replacement : null,
      supporting_references: decision === 'accept' ? references.filter(r => r.usable && selectedReferences.includes(r.reference.id)).map(r => r.reference) : []}); await onSaved()
  } catch (e) {setError((e as Error).message); onError((e as Error).message)} finally {setPending(false)} }}>
    <button type="button" className={styles.close} onClick={onClose}>Закрыть</button><h2>Запрос на пересмотр</h2><p><b>{criterion.title}</b></p>
    {error && <p role="alert" className={styles.error}>{error}</p>}
    <p>{appeal.author}: {appeal.reason}</p><p>Текущий результат: {current.answer ?? ({scored: 'Оценено', not_applicable: 'Не применимо', needs_review: 'Требует пересмотра'}[current.status])} · {current.explanation}</p>
    {current.uncertainty && <p className={styles.warning}><b>Требует уточнения: </b>{current.uncertainty}</p>}
    <label>Решение<select aria-label="Решение по запросу" value={decision} onChange={e => setDecision(e.target.value)}><option value="reject">Оставить оценку без изменений</option><option value="accept">Изменить оценку</option></select></label>
    {decision === 'accept' && <div className={styles.row}><label>Статус результата<select aria-label="Новый статус результата" value={status} onChange={e => setStatus(e.target.value as Judgment['status'])}><option value="scored">Оценено</option>{criterion.na_condition && <option value="not_applicable">Не применимо</option>}<option value="needs_review">Требует пересмотра</option></select></label>
      {status === 'scored' && <label>Новая оценка<select aria-label="Новая оценка" value={answer} onChange={e => setAnswer(e.target.value)}>{criterion.levels.map(l => <option key={l.value} value={l.value}>{l.value} · {l.description}</option>)}</select></label>}</div>}
    <label>Ваше имя<input aria-label="Имя проверяющего" required value={reviewer} onChange={e => setReviewer(e.target.value)}/></label>
    <label>Обоснование решения<textarea aria-label="Обоснование решения" required value={rationale} onChange={e => setRationale(e.target.value)}/></label>
    {decision === 'accept' && <fieldset><legend>Недостающие сведения</legend>
      <p>Оценка может быть выставлена с оговоркой. Не удаляйте её, пока не проверите недостающие сведения.</p>
      <label>Какие сведения ещё не подтверждены?<textarea aria-label="Неподтверждённые сведения" value={uncertainty} disabled={clearsUncertainty}
        onChange={e => {setUncertainty(e.target.value); setConfirmed(false)}}/></label>
      {hadUncertainty && status !== 'needs_review' && <label><input type="checkbox" aria-label="Подтвердить проверку недостающих сведений" checked={clearUncertainty}
        onChange={e => {setClearUncertainty(e.target.checked); setConfirmed(false)}}/> Я проверил недостающие сведения. Замечание можно снять.</label>}
      {clearsUncertainty && <label>Как вы подтвердили сведения?<textarea aria-label="Обоснование снятия замечания" required value={uncertaintyResolution}
        onChange={e => {setUncertaintyResolution(e.target.value); setConfirmed(false)}}/><small>Объяснение будет сохранено вместе с решением. Ниже выберите подтверждающие сообщения или документы.</small></label>}
      {!validUncertainty && <p className={styles.warning}>Сохраните замечание либо подтвердите проверку и опишите, как вы её провели.</p>}
    </fieldset>}
    {decision === 'accept' && <fieldset><legend>Сообщения, на которых основано решение</legend>
      <p>Укажите сообщения в поддержку решения и сообщения, которые ему противоречат. Они сохранятся как точные цитаты. Прежние цитаты не выбираются автоматически.</p>
      <div className={styles.messagePicker}>{messages.map(m => <label key={m.id}>
        <select aria-label={`Роль сообщения ${m.id}`} value={messageUses[m.id] || ''} onChange={e => {
          const value = e.target.value
          setMessageUses(old => {const next = {...old}; if (value) next[m.id] = value as 'support'|'counter'; else delete next[m.id]; return next})
          setConfirmed(false)
        }}><option value="">Не выбрано</option><option value="support">Подтверждает решение</option><option value="counter">Противоречит решению</option></select>
        {speakerName(m.speaker)} · {m.timestamp}: {m.text}
      </label>)}</div>
      <label><input type="checkbox" aria-label="Указать фрагмент с пропущенным действием" checked={checkOmission} onChange={e => {setCheckOmission(e.target.checked); setConfirmed(false)}}/> Я проверил фрагмент диалога и убедился, что нужное действие отсутствует.</label>
      {checkOmission && <><div className={styles.row}>
        <label>От сообщения<select aria-label="Начало проверенного фрагмента" value={omissionStart} onChange={e => {setOmissionStart(e.target.value); setConfirmed(false)}}><option value="">Выберите первое сообщение</option>{messages.map((m, i) => <option key={m.id} value={m.id}>Сообщение {i + 1} · {speakerName(m.speaker)} · {m.timestamp}</option>)}</select></label>
        <label>До сообщения<select aria-label="Конец проверенного фрагмента" value={omissionEnd} onChange={e => {setOmissionEnd(e.target.value); setConfirmed(false)}}><option value="">Выберите последнее сообщение</option>{messages.map((m, i) => <option key={m.id} value={m.id}>Сообщение {i + 1} · {speakerName(m.speaker)} · {m.timestamp}</option>)}</select></label>
      </div><p>{validInterval ? `Проверены сообщения ${startIndex + 1}–${endIndex + 1}. В обосновании укажите, какое действие отсутствует.` : 'Выберите начало и конец фрагмента, в котором должно было прозвучать нужное действие.'}</p></>}
      <p>В поддержку: {selectedEvidence.length} · Против: {selectedCounterevidence.length} · Проверено на отсутствие действия: {checkedIds.length}</p>
      {!hasDecisionEvidence && <p className={styles.muted}>Чтобы изменить оценку, выберите хотя бы одно подтверждающее сообщение или фрагмент, в котором отсутствует нужное действие.</p>}
    </fieldset>}
    {decision === 'accept' && <fieldset><legend>Подтверждающие документы</legend><p>Документы сохранятся вместе с решением. Исходная автоматическая оценка останется в истории. Выбрать можно только документы, подходящие для этой проверки.</p>
      {loadingSources && <p>Проверяем применимость документов…</p>}
      {references.map(({reference: r, usable, rejection_reasons: reasons}) => <label key={r.id}><input type="checkbox" disabled={!usable || loadingSources} checked={usable && selectedReferences.includes(r.id)} onChange={e => setSelectedReferences(old => e.target.checked ? [...old, r.id] : old.filter(id => id !== r.id))}/>
        {r.id} · {referenceDate(r)} · {usable ? 'Подходит' : `Не подходит: ${reasons.map(referenceReason).join('; ')}`}</label>)}</fieldset>}
    <label><input type="checkbox" aria-label="Я изучил критерий оценки, весь диалог и сообщения, приложенные к запросу." checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/> Я изучил критерий оценки, весь диалог и подтверждающие сообщения.</label>
    <p>Исходная автоматическая оценка сохранится. Итоговый балл будет пересчитан, а ваше решение останется в истории.</p>
    <button type="submit" className={styles.primary} disabled={!confirmed || pending || (decision === 'accept' && (!hasDecisionEvidence || !validUncertainty))}>Сохранить решение</button>
  </form></div>
}
