import type {Appeal, CitationSelection, ClaimOutcome, Evidence, HighlightRange, JobDetail, Reference, ReferenceEvidence} from './types'
import styles from './App.module.css'
import {date, dollars, terminal} from './format'

export function Highlighted({text, quote, ranges}: {text: string; quote?: string; ranges?: HighlightRange[]}) {
  if (ranges !== undefined) {
    const characters = Array.from(text)
    const valid = ranges.filter(r => Number.isInteger(r.start) && Number.isInteger(r.end)
      && r.start >= 0 && r.end > r.start && r.end <= characters.length
      && characters.slice(r.start, r.end).join('') === r.quote).sort((a, b) => a.start - b.start || a.end - b.end)
    const merged: {start: number; end: number}[] = []
    for (const range of valid) {
      const previous = merged[merged.length - 1]
      if (previous && range.start <= previous.end) previous.end = Math.max(previous.end, range.end)
      else merged.push({start: range.start, end: range.end})
    }
    let cursor = 0
    const pieces = merged.flatMap((range, i) => {
      const before = characters.slice(cursor, range.start).join('')
      cursor = range.end
      return [before, <mark key={i}>{characters.slice(range.start, range.end).join('')}</mark>]
    })
    return <>{pieces}{characters.slice(cursor).join('')}</>
  }
  if (!quote) return text
  const at = text.indexOf(quote)
  return at < 0 ? text : <>{text.slice(0, at)}<mark>{quote}</mark>{text.slice(at + quote.length)}</>
}
export function EvidenceButtons({items, onClick}: {items: Evidence[]; onClick: (e: Evidence[]) => void}) {
  return <div className={styles.evidence}>{items.map((e, i) => <button key={i} onClick={() => onClick([e])}>{e.message_id}: “{e.quote}”</button>)}
    {items.length > 1 && <button onClick={() => onClick(items)}>Show all cited spans</button>}</div>
}

export function Assessment({job, busy, onRetry, onCancel, onEvidence, onReference, onAppeal, onResolve}: {
  job: JobDetail; busy: boolean; onRetry: () => void; onCancel: () => void;
  onEvidence: (e: Evidence[], ids?: string[]) => void; onReference: (ref: Reference, quote?: string, selection?: CitationSelection) => void;
  onAppeal: (id: string) => void; onResolve: (a: Appeal) => void;
}) {
  const effective = job.effective, checklist = job.checklist.content
  const facts = job.record?.evaluation.factual_claims || []
  const paths = new WeakMap<object, string>()
  function indexSourceObjects(value: unknown, path: (string|number)[] = []) {
    if (value === null || typeof value !== 'object') return
    paths.set(value, path.map(part => '/' + String(part).replaceAll('~', '~0').replaceAll('/', '~1')).join(''))
    if (Array.isArray(value)) value.forEach((item, i) => indexSourceObjects(item, [...path, i]))
    else Object.entries(value).forEach(([key, item]) => indexSourceObjects(item, [...path, key]))
  }
  indexSourceObjects(job.record?.evaluation)
  function selectedSource(item: object): CitationSelection|undefined {
    const audit = job.record?.evaluation.source_citations, pointer = paths.get(item)
    if (!audit || pointer === undefined) return undefined
    const id = audit.selections[pointer], span = audit.spans?.[id]
    return {source_citation_expected: true, source_span_id: id,
      ...(span ? {source_id: span.source_id, source_kind: span.kind, source_field: span.field,
        source_start: span.start, source_end: span.end} : {})}
  }
  function citedEvidence(items: Evidence[], ids?: string[]) {
    onEvidence(items.map(item => ({...item, ...selectedSource(item)})), ids)
  }
  const assessment = effective?.assessment_context || job.record?.assessment_context || job.evidence_context?.assessment
  const flagged = Object.values(effective?.score.flags || {}).includes('yes')
  const flagUncertain = Object.values(effective?.score.flags || {}).includes('needs_review')
  function omissionRange(start: string, end: string) {
    const messages = job.conversation.content.messages
    const first = messages.findIndex(m => m.id === start), last = messages.findIndex(m => m.id === end)
    return first < 0 || last < first ? [] : messages.slice(first, last + 1).map(m => m.id)
  }
  function factReference(id: string) {
    const index = facts.findIndex(f => f.claim_id === id), fact = facts[index]
    const criterionIndex = fact ? checklist.criteria.findIndex(c => fact.criterion_ids.includes(c.id)) : -1
    const anchor = `fact-${index}-${criterionIndex}`
    return fact ? <a href={`#${anchor}`} onClick={event => {
      const target = document.getElementById(anchor)
      if (!target) return
      event.preventDefault()
      for (let parent = target.parentElement; parent; parent = parent.parentElement) {
        if (parent instanceof HTMLDetailsElement) parent.open = true
      }
      target.scrollIntoView({block: 'center'})
      target.focus({preventScroll: true})
    }}>{fact.claim} ({fact.status})</a> : <span>Unresolved fact reference: {id}</span>
  }
  function referenceButtons(items: ReferenceEvidence[]) {
    return items.map((r, n) => <button key={n} onClick={() => {
      const ref = job.conversation.content.references.find(x => x.id === r.reference_id)
      if (ref) onReference(ref, r.quote, selectedSource(r))
    }}>Reference: {r.reference_id} — {r.quote}</button>)
  }
  function outcome(value: ClaimOutcome) {
    return value.status === 'scored' ? value.answer : value.status.replaceAll('_', ' ')
  }
  return <>
    <div className={styles.card}><b data-testid="job-status">{job.status}</b> · {date(job.created_at)}
      <p>Checklist: {checklist.title} · {checklist.version}</p>
      {assessment?.conditional && <div className={styles.warning} data-testid="conditional-assessment"><b>Conditional snapshot assessment</b>
        <p>Assumed product scope: {assessment.scope} · Source snapshot as of {assessment.as_of}.</p>
        <p>Actual conversation date: {job.evidence_context?.temporal.occurred_on || job.conversation.content.occurred_on || 'unknown'}. This review does not verify historical policy applicability.</p>
        {assessment.rationale && <p>{assessment.rationale}</p>}</div>}
      {job.status === 'queued' && <button onClick={onCancel}>Cancel queued evaluation</button>}
      {job.status === 'running' && <p>Evaluating through the real OpenAI API… You can leave this page; the job continues.</p>}
      {terminal.has(job.status) && <button disabled={busy} onClick={onRetry}>{job.status === 'completed' ? 'Run again (billable)' : 'Retry (billable)'}</button>}
      {job.record?.error && <p role="alert" className={styles.error}>Evaluation failed: {job.record.error}. No substitute assessment was generated.</p>}
      {job.record?.validation_reason && <p>Validation: {job.record.validation_reason}</p>}
      {job.record?.repair_skipped && <p>Repair was not submitted: {job.record.repair_skipped}. A retry is a new paid attempt.</p>}
      {job.record?.error_detail && <p>{job.record.error_detail}. No API request was submitted for this job.</p>}
      {job.record?.budget_required_usd != null && <p>Required conservative allowance: {dollars(job.record.budget_required_usd)}; available: {dollars(job.record.budget_available_usd || 0)}. This includes one possible repair and is not an expected charge.</p>}
      {job.record?.usage && <p>{job.record.model} · {dollars(job.record.usage.estimated_cost_usd)} · {job.record.attempt_count} attempt(s) · {job.record.latency_seconds}s</p>}
      <a href={`/api/jobs/${job.id}/export`}>Export result and review history</a>
    </div>
    {effective && <>
      <div className={styles.score} data-testid="score"><strong>{effective.score.total === null ? 'Provisional' : `${effective.score.total}/100`}</strong>
        <span>{assessment?.conditional ? 'Conditional result · ' : ''}{effective.source === 'human_review' ? `Human-reviewed · ${effective.accepted_revisions} accepted revision(s)` : 'Saved AI assessment'}</span>
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
        const original = !changed && job.record?.evaluation.judgments.find(item => item.criterion_id === j.criterion_id)
        const judgmentEvidence = original || j
        return <article key={j.criterion_id} className={styles.card} data-testid={`criterion-${j.criterion_id}`}>
          <h3>{c.title} <small>{changed ? 'Human review' : 'AI'}</small></h3><b>{j.status === 'scored' ? j.answer : j.status}</b>
          <p>{j.explanation}</p>{j.uncertainty && <p className={styles.warning}>{j.uncertainty}</p>}
          <EvidenceButtons items={judgmentEvidence.evidence} onClick={citedEvidence}/>
          {judgmentEvidence.counterevidence.length > 0 && <><small>Counterevidence</small><EvidenceButtons items={judgmentEvidence.counterevidence} onClick={citedEvidence}/></>}
          <div className={styles.row}><button onClick={() => onEvidence([], j.checked_message_ids)}>Show checked messages</button>
            <button onClick={() => onAppeal(j.criterion_id)}>Appeal this judgment</button></div>
          <details><summary>Configured rule and original AI audit</summary><p>{c.instruction}</p>
            {job.record?.evaluation.deductions.filter(d => d.criterion_id === c.id).map((d, i) => <div key={i}><blockquote>{d.rule_quote}</blockquote><p>{d.defect}</p><p>{d.overlap_note}</p></div>)}
            {facts.filter(f => f.criterion_ids.includes(c.id)).map((f, i) => <div className={styles.fact} key={i}
              id={`fact-${facts.indexOf(f)}-${checklist.criteria.indexOf(c)}`} tabIndex={-1}
              data-testid={f.claim_id ? `fact-${f.claim_id}` : undefined}>
              <b>{f.status}</b><p>{f.claim}</p><p>{f.explanation}</p>
              {f.assertion_group_id && (() => {
                const group = job.record?.evaluation.assertion_groups?.find(g => g.group_id === f.assertion_group_id)
                return group ? <details><summary>{group.composition === 'all_of'
                  ? `Source statement contains ${group.claim_ids.length} separately assessed facts`
                  : 'Source statement contains one assessed fact'}</summary>
                  <p>Each fact keeps its own truth assessment and effect on the grade.</p>
                  <EvidenceButtons items={group.operator_evidence} onClick={citedEvidence}/>
                  {group.claim_ids.filter(id => id !== f.claim_id).map(id => <p key={id}>Related fact: {factReference(id)}</p>)}
                </details> : null
              })()}
              {f.verification_scope && <p>Verification scope: {f.verification_scope.replaceAll('_', ' ')}</p>}
              <small>Operator assertion</small><EvidenceButtons items={f.operator_evidence} onClick={citedEvidence}/>
              {f.dialogue_evidence.length > 0 && <><small>Recorded dialogue evidence</small>
                <p>Declared observation scope: {f.observation_scope?.replaceAll('_', ' ') || 'not recorded'}</p>
                {f.supported_proposition && (f.supported_proposition === f.claim
                  ? <p>Observation targets this claim.</p>
                  : <p>Declared observation proposition: {f.supported_proposition}</p>)}
                <EvidenceButtons items={f.dialogue_evidence} onClick={citedEvidence}/></>}
              {!f.dialogue_evidence.length && f.supported_proposition && (f.supported_proposition === f.claim
                ? <p>The supported proposition is this claim.</p>
                : <p>Declared supported proposition: {f.supported_proposition}</p>)}
              {f.proof && <div data-testid={`proof-${f.claim_id || i}`}>
                <b>{f.proof.relation === 'all_of' ? `All ${f.proof.required_premise_ids.length} proof premises are required` : 'Direct source proof'}</b>
                <p>{f.proof.explanation}</p>
                {f.proof.premises.map((p, n) => <div key={p.premise_id} data-testid={`premise-${f.claim_id || i}-${p.premise_id}`}>
                  <p><b>Premise {n + 1}{f.proof?.required_premise_ids.includes(p.premise_id) ? ' · required' : ''}</b></p>
                  {p.depends_on_claim_id ? <p>Requires {factReference(p.depends_on_claim_id)} to be {p.required_status}.</p>
                    : <><p>{p.proposition === null ? 'Uses this claim.' : p.proposition}</p>
                      <EvidenceButtons items={p.evidence} onClick={citedEvidence}/>
                      {referenceButtons(p.reference_evidence)}
                      {p.rule_evidence.map((r, key) => <div key={key}><small>Rule: {checklist.criteria.find(rule => rule.id === r.criterion_id)?.title || r.criterion_id}</small><blockquote>{r.quote}</blockquote></div>)}
                    </>}
                </div>)}
              </div>}
              {!!f.context_evidence?.length && <><small>Customer/system context — not independent verification</small>
                <EvidenceButtons items={f.context_evidence} onClick={citedEvidence}/></>}
              {referenceButtons(f.reference_evidence)}
              {f.assessment?.correction && <div><b>Earlier advice explicitly corrected</b>
                <p>{f.assessment.correction.explanation}</p>
                <p>Remaining consequence: {f.assessment.correction.remaining_consequence.replaceAll('_', ' ')}</p>
                <small>Correction</small><EvidenceButtons items={f.assessment.correction.operator_evidence} onClick={citedEvidence}/>
                <small>Independent outcome evidence</small><EvidenceButtons items={f.assessment.correction.outcome_evidence} onClick={citedEvidence}/>
                {referenceButtons(f.assessment.correction.reference_evidence)}
              </div>}
              {f.assessment?.impacts.filter(impact => impact.criterion_id === c.id).map(impact => <div key={impact.criterion_id}>
                <p>Grade if this fact were true: <b>{outcome(impact.when_true)}</b> · if false: <b>{outcome(impact.when_false)}</b></p>
                <p>{impact.explanation}</p>
                {impact.fixed_claim_ids && <><small>Other facts held fixed for this comparison</small>
                  {impact.fixed_claim_ids.length ? <ul>{impact.fixed_claim_ids.map(id => <li key={id}>{factReference(id)}</li>)}</ul>
                    : <p>No other related facts were declared.</p>}</>}
              </div>)}
            </div>)}
            {changed && <p>These audits belong to the original AI result. The human decision is recorded below.</p>}
          </details>
        </article>
      })}
      <details className={styles.card}><summary>Customer request coverage · original AI analysis</summary>{job.record?.evaluation.request_coverage.map((r, i) => {
        const support = r.support, omission = support?.omission
        const interval = omission ? omissionRange(omission.start_message_id, omission.end_message_id) : []
        return <div key={i}><b>{r.status}: {r.request}</b><p>{r.explanation}</p>
          <button onClick={() => onEvidence([], [...r.request_message_ids, ...r.answer_message_ids])}>Show linked request and operator turns</button>
          {support && <>
            {support.basis === 'none' ? <p>No operator answer recorded.</p> : <><p>{support.basis === 'withdrawn' ? 'Customer withdrawal evidence' : `Operator answer evidence (${support.basis.replaceAll('_', ' ')})`}</p>
              <EvidenceButtons items={support.evidence} onClick={citedEvidence}/></>}
            {support.inference && <p>Answer inference: {support.inference}</p>}
            {support.unresolved_aspects.length > 0 && <p>Still unanswered: {support.unresolved_aspects.join('; ')}</p>}
          </>}
          {omission && <div><p>Interval checked for missing answer: {omission.start_message_id}–{omission.end_message_id}</p>
            <button disabled={!interval.length} onClick={() => onEvidence([], interval)}>Show complete omission review interval</button>
            <p>Context for the missing answer — not operator answer proof</p><EvidenceButtons items={omission.context_evidence} onClick={citedEvidence}/>
          </div>}
        </div>
      })}</details>
      {job.record?.evaluation.scope_notes.map((n, i) => <p className={styles.muted} key={i}>{n}</p>)}
      {job.evidence_context && <details className={styles.card}><summary>{job.evidence_context_origin === 'captured_with_request' ? 'Context captured with the assessment request' : 'Reconstructed context for inspection'}</summary>
        {job.evidence_context_origin !== 'captured_with_request' && <p>The saved result has no captured reference context. This view uses the preserved input and current inspection rules; it does not establish which source eligibility information the original model received.</p>}
        <p>Actual date: {job.evidence_context.temporal.occurred_on || 'unknown'} · {job.evidence_context.temporal.origin.replaceAll('_', ' ')}.</p>
        <p>Assessment: {job.evidence_context.assessment.mode.replaceAll('_', ' ')} · {job.evidence_context.assessment.scope || 'scope unknown'} · {job.evidence_context.assessment.as_of || 'date unknown'}</p>
        {job.evidence_context.assessment.pack_id && <p>Source pack: {job.evidence_context.assessment.pack_id} · {job.evidence_context.assessment.pack_sha256}</p>}
        {job.evidence_context.references.map(r => <p key={r.reference_id}>{r.reference_id}: {r.usable ? 'Usable' : `Unavailable — ${r.rejection_reasons.join(', ').replaceAll('_', ' ')}`}</p>)}
      </details>}
      <h2>Appeals & decisions ({job.appeals.length})</h2>{job.appeals.map(a => <article key={a.id} className={styles.card} data-testid={`appeal-${a.criterion_id}`}>
        <b>{a.criterion_id} · {a.status}</b><p>{a.author}: {a.reason}</p><button onClick={() => onEvidence([], a.message_ids)}>Show appeal evidence</button>
        {a.status === 'open' ? <button onClick={() => onResolve(a)}>Review appeal</button> : <><p>{a.resolution?.reviewer}: {a.resolution?.rationale}</p><p>Before: {a.resolution?.before.answer ?? a.resolution?.before.status} → After: {a.resolution?.after.answer ?? a.resolution?.after.status}</p>
          {a.resolution?.supporting_references?.map(ref => <button key={ref.id} onClick={() => onReference(ref)}>Review source: {ref.id}</button>)}</>}
      </article>)}
      <details className={styles.card}><summary>Original AI JSON & provenance</summary><p>Response: {job.record?.response_id} · Prompt: {job.record?.prompt_version}</p>
        {job.record?.evaluation.source_citations && <p>Source citations: {Object.keys(job.record.evaluation.source_citations.selections).length} selections resolved from preserved originals. Quote text comes from the selected sources.</p>}
        <pre>{JSON.stringify(job.record, null, 2)}</pre></details>
    </>}
  </>
}
