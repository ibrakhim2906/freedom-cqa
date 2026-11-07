import type {Appeal, Evidence, JobDetail, Reference} from './types'
import styles from './App.module.css'
import {date, dollars, terminal} from './format'

export function Highlighted({text, quote}: {text: string; quote: string}) {
  const at = text.indexOf(quote)
  return at < 0 ? text : <>{text.slice(0, at)}<mark>{quote}</mark>{text.slice(at + quote.length)}</>
}
export function EvidenceButtons({items, onClick}: {items: Evidence[]; onClick: (e: Evidence[]) => void}) {
  return <div className={styles.evidence}>{items.map((e, i) => <button key={i} onClick={() => onClick([e])}>{e.message_id}: “{e.quote}”</button>)}</div>
}

export function Assessment({job, busy, onRetry, onCancel, onEvidence, onReference, onAppeal, onResolve}: {
  job: JobDetail; busy: boolean; onRetry: () => void; onCancel: () => void;
  onEvidence: (e: Evidence[], ids?: string[]) => void; onReference: (ref: Reference, quote?: string) => void;
  onAppeal: (id: string) => void; onResolve: (a: Appeal) => void;
}) {
  const effective = job.effective, checklist = job.checklist.content
  const flagged = Object.values(effective?.score.flags || {}).includes('yes')
  const flagUncertain = Object.values(effective?.score.flags || {}).includes('needs_review')
  return <>
    <div className={styles.card}><b data-testid="job-status">{job.status}</b> · {date(job.created_at)}
      <p>Checklist: {checklist.title} · {checklist.version}</p>
      {job.status === 'queued' && <button onClick={onCancel}>Cancel queued evaluation</button>}
      {job.status === 'running' && <p>Evaluating through the real OpenAI API… You can leave this page; the job continues.</p>}
      {terminal.has(job.status) && <button disabled={busy} onClick={onRetry}>{job.status === 'completed' ? 'Run again (billable)' : 'Retry (billable)'}</button>}
      {job.record?.error && <p role="alert" className={styles.error}>Evaluation failed: {job.record.error}. No substitute assessment was generated.</p>}
      {job.record?.usage && <p>{job.record.model} · {dollars(job.record.usage.estimated_cost_usd)} · {job.record.attempt_count} attempt(s) · {job.record.latency_seconds}s</p>}
      <a href={`/api/jobs/${job.id}/export`}>Export result and review history</a>
    </div>
    {effective && <>
      <div className={styles.score} data-testid="score"><strong>{effective.score.total === null ? 'Provisional' : `${effective.score.total}/100`}</strong>
        <span>{effective.source === 'human_review' ? `Human-reviewed · ${effective.accepted_revisions} accepted revision(s)` : 'Saved AI assessment'}</span>
        {effective.score.provisional && <span>Allowed score range: {effective.score.score_bounds.lower}–{effective.score.score_bounds.upper}. Needs review: {effective.score.unresolved_criteria.join(', ')}</span>}
        {effective.source === 'human_review' && <span>Original AI total: {job.record?.score.total ?? 'provisional'}. Original output is preserved.</span>}
      </div>
      {Object.keys(effective.score.flags).length > 0 && <div role={flagged ? 'alert' : undefined} className={flagged ? styles.error : flagUncertain ? styles.warning : styles.card}>
        <b>Separate flags — excluded from the numeric score</b>
        {Object.entries(effective.score.flags).map(([id, value]) => <p key={id}>{checklist.criteria.find(c => c.id === id)?.title || id}: <strong>{value}</strong></p>)}
      </div>}
      {effective.judgments.map(j => {
        const c = checklist.criteria.find(c => c.id === j.criterion_id)!
        const changed = job.appeals.some(a => a.criterion_id === j.criterion_id && a.status === 'accepted')
        return <article key={j.criterion_id} className={styles.card} data-testid={`criterion-${j.criterion_id}`}>
          <h3>{c.title} <small>{changed ? 'Human review' : 'AI'}</small></h3><b>{j.status === 'scored' ? j.answer : j.status}</b>
          <p>{j.explanation}</p>{j.uncertainty && <p className={styles.warning}>{j.uncertainty}</p>}
          <EvidenceButtons items={j.evidence} onClick={onEvidence}/>
          {j.counterevidence.length > 0 && <><small>Counterevidence</small><EvidenceButtons items={j.counterevidence} onClick={onEvidence}/></>}
          <div className={styles.row}><button onClick={() => onEvidence([], j.checked_message_ids)}>Show checked messages</button>
            <button onClick={() => onAppeal(j.criterion_id)}>Appeal this judgment</button></div>
          <details><summary>Configured rule and original AI audit</summary><p>{c.instruction}</p>
            {job.record?.evaluation.deductions.filter(d => d.criterion_id === c.id).map((d, i) => <div key={i}><blockquote>{d.rule_quote}</blockquote><p>{d.defect}</p><p>{d.overlap_note}</p></div>)}
            {job.record?.evaluation.factual_claims.filter(f => f.criterion_ids.includes(c.id)).map((f, i) => <div className={styles.fact} key={i}>
              <b>{f.status}</b><p>{f.claim}</p><p>{f.explanation}</p><EvidenceButtons items={[...f.operator_evidence, ...f.dialogue_evidence]} onClick={onEvidence}/>
              {f.reference_evidence.map((r, n) => <button key={n} onClick={() => {const ref = job.conversation.content.references.find(x => x.id === r.reference_id); if (ref) onReference(ref, r.quote)}}>Reference: {r.reference_id} — {r.quote}</button>)}
            </div>)}
            {changed && <p>These audits belong to the original AI result. The human decision is recorded below.</p>}
          </details>
        </article>
      })}
      <details className={styles.card}><summary>Customer request coverage · original AI analysis</summary>{job.record?.evaluation.request_coverage.map((r, i) => <div key={i}><b>{r.status}: {r.request}</b><p>{r.explanation}</p><button onClick={() => onEvidence([], [...r.request_message_ids, ...r.answer_message_ids])}>Show request and answer</button></div>)}</details>
      {job.record?.evaluation.scope_notes.map((n, i) => <p className={styles.muted} key={i}>{n}</p>)}
      <h2>Appeals & decisions ({job.appeals.length})</h2>{job.appeals.map(a => <article key={a.id} className={styles.card} data-testid={`appeal-${a.criterion_id}`}>
        <b>{a.criterion_id} · {a.status}</b><p>{a.author}: {a.reason}</p><button onClick={() => onEvidence([], a.message_ids)}>Show appeal evidence</button>
        {a.status === 'open' ? <button onClick={() => onResolve(a)}>Review appeal</button> : <><p>{a.resolution?.reviewer}: {a.resolution?.rationale}</p><p>Before: {a.resolution?.before.answer ?? a.resolution?.before.status} → After: {a.resolution?.after.answer ?? a.resolution?.after.status}</p>
          {a.resolution?.supporting_references?.map(ref => <button key={ref.id} onClick={() => onReference(ref)}>Review source: {ref.id}</button>)}</>}
      </article>)}
      <details className={styles.card}><summary>Original AI JSON & provenance</summary><p>Response: {job.record?.response_id} · Prompt: {job.record?.prompt_version}</p><pre>{JSON.stringify(job.record, null, 2)}</pre></details>
    </>}
  </>
}
