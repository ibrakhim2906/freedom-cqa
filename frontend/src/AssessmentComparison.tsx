import {useState} from 'react'
import type {JobDetail, JobRow} from './types'
import {api} from './api'
import {date} from './format'
import styles from './App.module.css'

type ComparedDecision = {status: string; answer: string|null; contribution: number|null; explanation: string; uncertainty?: string|null}
type Comparison = {
  before_id: string; after_id: string; same_conversation: boolean; source_changed: boolean; checklist_changed: boolean;
  context_changed?: boolean; input_changed?: boolean;
  before_score: number|null; after_score: number|null; score_delta: number|null;
  before_provisional?: boolean; after_provisional?: boolean;
  before_result_source: string; after_result_source: string;
  criteria: {criterion_id: string; title: string; before: ComparedDecision|null; after: ComparedDecision|null;
    outcome_changed: boolean; rule_changed: boolean; added: boolean; removed: boolean}[];
}
function answer(decision: ComparedDecision|null) {
  if (!decision) return 'Not in checklist'
  if (decision.status === 'not_applicable') return 'N/A'
  if (decision.status === 'needs_review') return 'Needs review'
  return decision.answer ?? 'Unresolved'
}

export function AssessmentComparison({job, jobs}: {job: JobDetail; jobs: JobRow[]}) {
  // App keys this component by job.id, so every selected job starts a fresh comparison.
  const [candidates, setCandidates] = useState<JobRow[]>(), [candidatesPending, setCandidatesPending] = useState(false)
  const [candidatesError, setCandidatesError] = useState('')
  const choices = [...new Map([...jobs, ...(candidates || [])].map(j => [j.id, j])).values()]
    .filter(j => j.id !== job.id && j.status === 'completed').sort((a, b) => b.created_at.localeCompare(a.created_at))
  const [baseline, setBaseline] = useState(''), [result, setResult] = useState<Comparison>()
  const [pending, setPending] = useState(false), [error, setError] = useState(''), [showAll, setShowAll] = useState(false)
  const changed = result?.criteria.filter(c => c.outcome_changed || c.rule_changed || c.added || c.removed) || []
  const shown = showAll ? result?.criteria || [] : changed
  async function loadCandidates() {
    if (candidates !== undefined || candidatesPending) return
    setCandidatesPending(true); setCandidatesError('')
    try {setCandidates(await api<JobRow[]>(`/jobs/${job.id}/comparison-candidates`))}
    catch (e) {setCandidatesError((e as Error).message)} finally {setCandidatesPending(false)}
  }
  if (!job.effective) return null
  return <details className={styles.comparison} onToggle={event => {if (event.currentTarget.open) void loadCandidates()}}>
    <summary>Compare saved assessments</summary>
    <p>Compare saved results across revisions of this conversation. Comparison makes no model call.</p>
    {candidatesPending && <p className={styles.muted} role="status">Finding assessments across saved revisions…</p>}
    {candidatesError && <p className={styles.warning}>Other saved revisions could not be loaded: {candidatesError} <button onClick={() => void loadCandidates()}>Try again</button></p>}
    {choices.length ? <div className={styles.compareControls}>
      <select aria-label="Baseline assessment" value={baseline} disabled={pending} onChange={e => {setBaseline(e.target.value); setResult(undefined); setError('')}}>
        <option value="">Choose a baseline assessment</option>{choices.map(j => <option key={j.id} value={j.id}>{date(j.created_at)} · {j.id.slice(0, 7)}{j.conversation_id !== job.conversation_id ? ' · other saved revision' : ''}{j.review_revision ? ' · reviewed' : ''}</option>)}
      </select>
      <button disabled={!baseline || pending} onClick={async () => {
        setPending(true); setError(''); setResult(undefined)
        try {setResult(await api<Comparison>(`/jobs/${job.id}/compare?baseline=${encodeURIComponent(baseline)}`))}
        catch (e) {setError((e as Error).message)} finally {setPending(false)}
      }}>{pending ? 'Comparing…' : 'Compare results'}</button>
    </div> : !candidatesPending && !candidatesError && <p className={styles.muted}>Another completed assessment of this conversation is needed. Saved results from other transcript or evidence-context revisions can also be compared here.</p>}
    {error && <p className={styles.error} role="alert">{error}</p>}
    {result && <div data-testid="assessment-comparison">
      <div className={styles.compareScores}><div><span>Baseline</span><strong>{result.before_score ?? 'Not recorded'}</strong>{result.before_provisional && <small>Provisional assessment</small>}<small>{result.before_result_source === 'human_review' ? 'Human-reviewed' : 'AI assessment'}</small></div>
        <div aria-hidden="true">→</div><div><span>Selected result</span><strong>{result.after_score ?? 'Not recorded'}</strong>{result.after_provisional && <small>Provisional assessment</small>}<small>{result.after_result_source === 'human_review' ? 'Human-reviewed' : 'AI assessment'}</small></div>
        {result.score_delta !== null && <div className={styles.compareDelta}>{result.score_delta > 0 ? '+' : ''}{result.score_delta}<small>{result.before_provisional || result.after_provisional ? 'provisional score difference' : 'score difference'}</small></div>}
      </div>
      {!result.same_conversation && <p className={styles.warning}>These assessments use different saved conversation documents. Check the transcript and evidence-context differences before interpreting the score change.</p>}
      <p>{result.source_changed ? 'Source transcript changed.' : 'Source transcript unchanged.'} {result.context_changed !== undefined && (result.context_changed ? 'Evidence or assessment context changed. ' : 'Evidence and assessment context unchanged. ')}{result.checklist_changed ? 'Checklist configuration changed.' : 'Checklist configuration unchanged.'}</p>
      <div className={styles.row}><b>{changed.length} changed criteria</b><button className={styles.quiet} onClick={() => setShowAll(!showAll)}>{showAll ? 'Show changes only' : 'Show all criteria'}</button></div>
      {!shown.length && <p className={styles.muted}>No criterion decisions or rules changed.</p>}
      {shown.map(c => <div className={styles.compareCriterion} key={c.criterion_id}><div><b>{c.title}</b><span>{c.added ? 'Added' : c.removed ? 'Removed' : c.rule_changed ? 'Rule changed' : c.outcome_changed ? 'Decision changed' : 'Unchanged'}</span></div>
        <p>{answer(c.before)} <span aria-label="to">→</span> {answer(c.after)}</p>
        <details><summary>Compare explanations</summary>{c.before && <><small>Baseline explanation</small><p>{c.before.explanation}</p>{c.before.uncertainty && <p className={styles.warning}><b>Baseline review note: </b>{c.before.uncertainty}</p>}</>}{c.after && <><small>Selected explanation</small><p>{c.after.explanation}</p>{c.after.uncertainty && <p className={styles.warning}><b>Selected review note: </b>{c.after.uncertainty}</p>}</>}
          <p className={styles.muted}>Weighted contribution before N/A normalization: {c.before?.contribution ?? '—'} → {c.after?.contribution ?? '—'}. This is not an isolated effect on the total.</p>
        </details>
      </div>)}
    </div>}
  </details>
}
