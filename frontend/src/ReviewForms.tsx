import {useEffect, useState} from 'react'
import type {Appeal, JobDetail, Judgment, ReferenceOption} from './types'
import {api} from './api'
import {referenceDate} from './format'
import styles from './App.module.css'

type Shared = {job: JobDetail; onClose: () => void; onSaved: () => Promise<void>; onError: (s: string) => void}
export function AppealForm({job, criterionId, onClose, onSaved, onError}: Shared & {criterionId: string}) {
  const [author, setAuthor] = useState(''), [reason, setReason] = useState(''), [ids, setIds] = useState<string[]>([]), [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  return <div className={styles.overlay}><form className={styles.dialog} role="dialog" aria-modal="true" aria-label="Submit criterion appeal" onSubmit={async e => {e.preventDefault(); setPending(true); try {
    await api(`/jobs/${job.id}/appeals`, {criterion_id: criterionId, author, reason, message_ids: ids}); await onSaved()
  } catch (e) {setError((e as Error).message); onError((e as Error).message)} finally {setPending(false)} }}>
    <button type="button" className={styles.close} onClick={onClose}>Close appeal</button><h2>Appeal: {criterionId}</h2>
    {error && <p role="alert" className={styles.error}>{error}</p>}
    <label>Your name<input aria-label="Appeal author" required value={author} onChange={e => setAuthor(e.target.value)}/></label>
    <label>Why should this judgment be reviewed?<textarea aria-label="Appeal reason" required value={reason} onChange={e => setReason(e.target.value)}/></label>
    <p>Select supporting source messages:</p><div className={styles.messagePicker}>{job.conversation.content.messages.map(m => <label key={m.id}><input type="checkbox" checked={ids.includes(m.id)} onChange={e => setIds(old => e.target.checked ? [...old, m.id] : old.filter(id => id !== m.id))}/>{m.id} · {m.speaker}: {m.text}</label>)}</div>
    <button type="submit" className={styles.primary} disabled={!ids.length || pending}>Submit appeal</button>
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
  return <div className={styles.overlay}><form className={styles.dialog} role="dialog" aria-modal="true" aria-label="Review criterion appeal" onSubmit={async e => {e.preventDefault(); if (decision === 'accept' && !hasDecisionEvidence) {setError('Select supporting messages or a valid interval checked for an omission.'); return} if (decision === 'accept' && !validUncertainty) {setError('Retain the unresolved information, or explicitly mark it resolved and explain the supporting basis.'); return} setPending(true); try {
    const decisionRationale = decision === 'accept' && clearsUncertainty
      ? `${rationale.trim()}\n\nUncertainty resolved: ${uncertaintyResolution.trim()}` : rationale
    const replacement: Judgment = {criterion_id: appeal.criterion_id, status, answer: status === 'scored' ? answer : null,
      explanation: decisionRationale, evidence: selectedEvidence, counterevidence: selectedCounterevidence,
      checked_message_ids: checkedIds, uncertainty: clearsUncertainty ? null : uncertainty.trim() || (status === 'needs_review' ? rationale : null)}
    await api(`/appeals/${appeal.id}/resolve`, {decision, reviewer, rationale: decisionRationale, expected_revision: job.review_revision, judgment: decision === 'accept' ? replacement : null,
      supporting_references: decision === 'accept' ? references.filter(r => r.usable && selectedReferences.includes(r.reference.id)).map(r => r.reference) : []}); await onSaved()
  } catch (e) {setError((e as Error).message); onError((e as Error).message)} finally {setPending(false)} }}>
    <button type="button" className={styles.close} onClick={onClose}>Close review</button><h2>Review appeal: {appeal.criterion_id}</h2>
    {error && <p role="alert" className={styles.error}>{error}</p>}
    <p>{appeal.author}: {appeal.reason}</p><p>Current judgment: {current.answer ?? current.status} · {current.explanation}</p>
    {current.uncertainty && <p className={styles.warning}><b>Current uncertainty: </b>{current.uncertainty}</p>}
    <label>Decision<select aria-label="Appeal decision" value={decision} onChange={e => setDecision(e.target.value)}><option value="reject">Reject — keep current judgment</option><option value="accept">Accept — replace this judgment</option></select></label>
    {decision === 'accept' && <div className={styles.row}><label>Status<select aria-label="Reviewed status" value={status} onChange={e => setStatus(e.target.value as Judgment['status'])}><option value="scored">Scored</option>{criterion.na_condition && <option value="not_applicable">N/A</option>}<option value="needs_review">Needs review</option></select></label>
      {status === 'scored' && <label>Answer<select aria-label="Reviewed answer" value={answer} onChange={e => setAnswer(e.target.value)}>{criterion.levels.map(l => <option key={l.value} value={l.value}>{l.value} · {l.description}</option>)}</select></label>}</div>}
    <label>Reviewer<input aria-label="Reviewer name" required value={reviewer} onChange={e => setReviewer(e.target.value)}/></label>
    <label>Decision rationale<textarea aria-label="Decision rationale" required value={rationale} onChange={e => setRationale(e.target.value)}/></label>
    {decision === 'accept' && <fieldset><legend>Uncertainty in the reviewed judgment</legend>
      <p>A numerical grade can retain unresolved facts. Keep them visible unless your review establishes the missing information.</p>
      <label>Information still unverified<textarea aria-label="Reviewed uncertainty" value={uncertainty} disabled={clearsUncertainty}
        onChange={e => {setUncertainty(e.target.value); setConfirmed(false)}}/></label>
      {hadUncertainty && status !== 'needs_review' && <label><input type="checkbox" aria-label="Mark uncertainty resolved" checked={clearUncertainty}
        onChange={e => {setClearUncertainty(e.target.checked); setConfirmed(false)}}/> The missing information is resolved; clear this uncertainty.</label>}
      {clearsUncertainty && <label>How was the missing information established?<textarea aria-label="Uncertainty resolution rationale" required value={uncertaintyResolution}
        onChange={e => {setUncertaintyResolution(e.target.value); setConfirmed(false)}}/><small>This explanation is saved with the decision. Select the evidence supporting it below.</small></label>}
      {!validUncertainty && <p className={styles.warning}>Retain the missing-information note, or mark it resolved and explain the supporting basis.</p>}
    </fieldset>}
    {decision === 'accept' && <fieldset><legend>Evidence for your new judgment</legend>
      <p>Select the messages that support your decision and any counterevidence. The disputed judgment's evidence is not copied. Selected messages are saved as exact source quotes.</p>
      <div className={styles.messagePicker}>{messages.map(m => <label key={m.id}>
        <select aria-label={`Use message ${m.id}`} value={messageUses[m.id] || ''} onChange={e => {
          const value = e.target.value
          setMessageUses(old => {const next = {...old}; if (value) next[m.id] = value as 'support'|'counter'; else delete next[m.id]; return next})
          setConfirmed(false)
        }}><option value="">Not selected</option><option value="support">Supports my judgment</option><option value="counter">Counterevidence</option></select>
        {m.id} · {m.timestamp} · {m.speaker}: {m.text}
      </label>)}</div>
      <label><input type="checkbox" aria-label="Check an omission interval" checked={checkOmission} onChange={e => {setCheckOmission(e.target.checked); setConfirmed(false)}}/> I checked an interval for missing behavior.</label>
      {checkOmission && <><div className={styles.row}>
        <label>From<select aria-label="Omission interval start" value={omissionStart} onChange={e => {setOmissionStart(e.target.value); setConfirmed(false)}}><option value="">Select first message</option>{messages.map(m => <option key={m.id} value={m.id}>{m.id} · {m.speaker} · {m.timestamp}</option>)}</select></label>
        <label>Through<select aria-label="Omission interval end" value={omissionEnd} onChange={e => {setOmissionEnd(e.target.value); setConfirmed(false)}}><option value="">Select last message</option>{messages.map(m => <option key={m.id} value={m.id}>{m.id} · {m.speaker} · {m.timestamp}</option>)}</select></label>
      </div><p>{validInterval ? `Checked interval: ${checkedIds.join(', ')}. Explain what was missing in your rationale.` : 'Select an ordered interval containing the opportunity for the missing behavior.'}</p></>}
      <p>{selectedEvidence.length} supporting message(s) · {selectedCounterevidence.length} counterevidence message(s) · {checkedIds.length} messages checked for omission.</p>
      {!hasDecisionEvidence && <p className={styles.muted}>Choose at least one supporting message or a checked omission interval before accepting.</p>}
    </fieldset>}
    {decision === 'accept' && <fieldset><legend>Additional reference evidence</legend><p>Selected sources are saved with this human decision. Original AI inputs stay unchanged. Only sources applicable to this saved assessment context can be selected.</p>
      {loadingSources && <p>Checking source applicability…</p>}
      {references.map(({reference: r, usable, rejection_reasons: reasons}) => <label key={r.id}><input type="checkbox" disabled={!usable || loadingSources} checked={usable && selectedReferences.includes(r.id)} onChange={e => setSelectedReferences(old => e.target.checked ? [...old, r.id] : old.filter(id => id !== r.id))}/>
        {r.id} · {referenceDate(r)} · {usable ? 'Usable' : `Unavailable — ${reasons.join(', ').replaceAll('_', ' ')}`}</label>)}</fieldset>}
    <label><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/> I reviewed the criterion, the full source transcript and the appeal evidence.</label>
    <p>The original AI output stays unchanged. Accepted decisions recalculate the final score and are marked as human review.</p>
    <button type="submit" className={styles.primary} disabled={!confirmed || pending || (decision === 'accept' && (!hasDecisionEvidence || !validUncertainty))}>Save review decision</button>
  </form></div>
}
