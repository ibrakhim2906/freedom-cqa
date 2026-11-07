import {useEffect, useState} from 'react'
import type {Appeal, JobDetail, Judgment, Reference} from './types'
import {api} from './api'
import styles from './App.module.css'

type Shared = {job: JobDetail; onClose: () => void; onSaved: () => Promise<void>; onError: (s: string) => void}
export function AppealForm({job, criterionId, onClose, onSaved, onError}: Shared & {criterionId: string}) {
  const [author, setAuthor] = useState(''), [reason, setReason] = useState(''), [ids, setIds] = useState<string[]>([]), [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  return <div className={styles.overlay}><form className={styles.dialog} onSubmit={async e => {e.preventDefault(); setPending(true); try {
    await api(`/jobs/${job.id}/appeals`, {criterion_id: criterionId, author, reason, message_ids: ids}); await onSaved()
  } catch (e) {setError((e as Error).message); onError((e as Error).message)} finally {setPending(false)} }}>
    <button type="button" className={styles.close} onClick={onClose}>Close appeal</button><h2>Appeal: {criterionId}</h2>
    {error && <p role="alert" className={styles.error}>{error}</p>}
    <label>Your name<input aria-label="Appeal author" required value={author} onChange={e => setAuthor(e.target.value)}/></label>
    <label>Why should this judgment be reviewed?<textarea aria-label="Appeal reason" required value={reason} onChange={e => setReason(e.target.value)}/></label>
    <p>Select supporting source messages:</p><div className={styles.messagePicker}>{job.conversation.content.messages.map(m => <label key={m.id}><input type="checkbox" checked={ids.includes(m.id)} onChange={e => setIds(old => e.target.checked ? [...old, m.id] : old.filter(id => id !== m.id))}/>{m.id} · {m.speaker}: {m.text}</label>)}</div>
    <button type="submit" disabled={!ids.length || pending}>Submit appeal</button>
  </form></div>
}

export function ResolveForm({job, appeal, onClose, onSaved, onError}: Shared & {appeal: Appeal}) {
  const current = job.effective!.judgments.find(j => j.criterion_id === appeal.criterion_id)!
  const criterion = job.checklist.content.criteria.find(c => c.id === appeal.criterion_id)!
  const [decision, setDecision] = useState('reject'), [reviewer, setReviewer] = useState(''), [rationale, setRationale] = useState('')
  const [status, setStatus] = useState<Judgment['status']>(current.status), [answer, setAnswer] = useState(current.answer || criterion.levels[0].value)
  const [pending, setPending] = useState(false), [confirmed, setConfirmed] = useState(false)
  const [error, setError] = useState('')
  const [references, setReferences] = useState<Reference[]>([]), [selectedReferences, setSelectedReferences] = useState<string[]>([])
  useEffect(() => {api<{references: Reference[]}[]>('/reference-packs').then(packs => setReferences(packs.flatMap(p => p.references))).catch(e => onError(e.message))}, [onError])
  return <div className={styles.overlay}><form className={styles.dialog} onSubmit={async e => {e.preventDefault(); setPending(true); try {
    const replacement: Judgment = {...current, status, answer: status === 'scored' ? answer : null,
      explanation: rationale, checked_message_ids: job.conversation.content.messages.map(m => m.id), uncertainty: status === 'needs_review' ? rationale : null}
    await api(`/appeals/${appeal.id}/resolve`, {decision, reviewer, rationale, expected_revision: job.review_revision, judgment: decision === 'accept' ? replacement : null,
      supporting_references: references.filter(r => selectedReferences.includes(r.id))}); await onSaved()
  } catch (e) {setError((e as Error).message); onError((e as Error).message)} finally {setPending(false)} }}>
    <button type="button" className={styles.close} onClick={onClose}>Close review</button><h2>Review appeal: {appeal.criterion_id}</h2>
    {error && <p role="alert" className={styles.error}>{error}</p>}
    <p>{appeal.author}: {appeal.reason}</p><p>Current judgment: {current.answer ?? current.status} · {current.explanation}</p>
    <label>Decision<select aria-label="Appeal decision" value={decision} onChange={e => setDecision(e.target.value)}><option value="reject">Reject — keep current judgment</option><option value="accept">Accept — replace this judgment</option></select></label>
    {decision === 'accept' && <div className={styles.row}><label>Status<select aria-label="Reviewed status" value={status} onChange={e => setStatus(e.target.value as Judgment['status'])}><option value="scored">Scored</option>{criterion.na_condition && <option value="not_applicable">N/A</option>}<option value="needs_review">Needs review</option></select></label>
      {status === 'scored' && <label>Answer<select aria-label="Reviewed answer" value={answer} onChange={e => setAnswer(e.target.value)}>{criterion.levels.map(l => <option key={l.value} value={l.value}>{l.value} · {l.description}</option>)}</select></label>}</div>}
    <label>Reviewer<input aria-label="Reviewer name" required value={reviewer} onChange={e => setReviewer(e.target.value)}/></label>
    <label>Decision rationale<textarea aria-label="Decision rationale" required value={rationale} onChange={e => setRationale(e.target.value)}/></label>
    {decision === 'accept' && <fieldset><legend>Additional reference evidence</legend><p>Selected sources are saved with this human decision. Original AI inputs stay unchanged. Scope and date must match.</p>
      {references.map(r => <label key={r.id}><input type="checkbox" checked={selectedReferences.includes(r.id)} onChange={e => setSelectedReferences(old => e.target.checked ? [...old, r.id] : old.filter(id => id !== r.id))}/>{r.id} · {r.valid_from}–{r.valid_until}</label>)}</fieldset>}
    <label><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/> I reviewed the criterion, the full source transcript and the appeal evidence.</label>
    <p>The original AI output stays unchanged. Accepted decisions recalculate the final score and are marked as human review.</p>
    <button type="submit" disabled={!confirmed || pending}>Save review decision</button>
  </form></div>
}
