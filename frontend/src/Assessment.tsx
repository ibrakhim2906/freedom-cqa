import type {Appeal, Checklist, CitationSelection, ClaimOutcome, Evidence, HighlightRange, JobDetail, Reference, ReferenceEvidence} from './types'
import styles from './App.module.css'
import {date, dollars, terminal} from './format'
import {Icon} from './Icon'

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
  const reviewCriteria = new Set([...(effective?.score.unresolved_criteria || []), ...(effective?.score.review_recommended_criteria || [])])
  const facts = job.record?.evaluation?.factual_claims || []
  const paths = new WeakMap<object, string>()
  function indexSourceObjects(value: unknown, path: (string|number)[] = []) {
    if (value === null || typeof value !== 'object') return
    paths.set(value, path.map(part => '/' + String(part).replaceAll('~', '~0').replaceAll('/', '~1')).join(''))
    if (Array.isArray(value)) value.forEach((item, i) => indexSourceObjects(item, [...path, i]))
    else Object.entries(value).forEach(([key, item]) => indexSourceObjects(item, [...path, key]))
  }
  indexSourceObjects(job.record?.evaluation)
  const nativeSelections = new WeakMap<object, CitationSelection>()
  const nativeAssessment = job.record?.assessment
  if (nativeAssessment?.transport && nativeAssessment.source_selections) {
    const selections = nativeAssessment.source_selections
    function bind(items: object[], ids: string[]) {
      items.forEach((item, index) => {
        const id = ids[index], span = selections[id]
        nativeSelections.set(item, {source_citation_expected: true, source_span_id: id,
          ...(span ? {source_id: span.source_id, source_kind: span.kind, source_field: span.field,
            source_start: span.start, source_end: span.end} : {})})
      })
    }
    for (const judgment of job.record?.evaluation?.judgments || []) {
      const wire = nativeAssessment.transport.judgments[judgment.criterion_id]
      if (!wire) continue
      bind(judgment.evidence, wire.evidence_span_ids)
      bind(judgment.counterevidence, wire.counterevidence_span_ids)
      const resolved = nativeAssessment.criteria[judgment.criterion_id]
      if (resolved) {
        bind(resolved.factual_dialogue_evidence, wire.factual_support_span_ids.filter(id => selections[id]?.kind === 'dialogue'))
        bind(resolved.reference_evidence, wire.factual_support_span_ids.filter(id => selections[id]?.kind === 'reference'))
      }
    }
  }
  function selectedSource(item: object): CitationSelection|undefined {
    if (nativeSelections.has(item)) return nativeSelections.get(item)
    const audit = job.record?.evaluation?.source_citations, pointer = paths.get(item)
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
    <div className={styles.jobTop}><b className={styles.status} data-status={job.status} data-testid="job-status">{job.status}</b><span>{date(job.created_at)}</span></div>
    {assessment?.conditional && <div className={styles.warning} data-testid="conditional-assessment"><b>Conditional snapshot assessment</b>
      <p>Assumed product scope: {assessment.scope} · Source snapshot as of {assessment.as_of}.</p>
      <p>Actual conversation date: {job.evidence_context?.temporal.occurred_on || job.conversation.content.occurred_on || 'unknown'}. This review does not verify historical policy applicability.</p>
      {assessment.rationale && <p>{assessment.rationale}</p>}</div>}
    {job.status === 'queued' && <div className={styles.card}><p>This conversation is waiting in the evaluation queue.</p><button onClick={onCancel}>Cancel queued evaluation</button></div>}
    {job.status === 'running' && <div className={styles.card} role="status"><p>Reading the conversation and checking the selected criteria…</p><p className={styles.muted}>The evaluation continues if you leave this page.</p></div>}
    {job.record?.error && <div role="alert" className={styles.error} style={{marginTop: 14}}><b>{failureTitle(job.record.error)}</b>
      <p>{failureAdvice(job.record.error)}</p>
      {job.record.error_detail && <p>{job.record.error_detail}</p>}
      {job.record.budget_required_usd != null && <p>This attempt requires an allowance of {dollars(job.record.budget_required_usd)}; available: {dollars(job.record.budget_available_usd || 0)}. This protects a first request and one possible repair; it is not an expected charge.</p>}
      <details><summary>Failure details</summary><p>{job.record.error}</p>{job.record.validation_reason && <p>{job.record.validation_reason}</p>}{job.record.repair_skipped && <p>Repair was not submitted: {job.record.repair_skipped}.</p>}</details>
    </div>}
    <details className={styles.jobDetails}><summary>Assessment details & export</summary><div className={styles.jobMeta}>
      <span>Checklist: {checklist.title} · {checklist.version}</span>
      {job.record?.usage && <span>{job.record.model} · {dollars(job.record.usage.estimated_cost_usd)} · {job.record.attempt_count} attempt(s) · {job.record.latency_seconds}s</span>}
      <a href={`/api/jobs/${job.id}/export`}>Export result and review history</a>
      {job.status === 'completed' && <button disabled={busy} onClick={onRetry}>Run again (billable)</button>}
    </div></details>
    {terminal.has(job.status) && job.status !== 'completed' && <div className={styles.row} style={{marginTop: 12}}><button disabled={busy} onClick={onRetry}>Retry (billable)</button><span className={styles.muted}>The previous attempt is preserved.</span></div>}
    {effective && <>
      <div className={`${styles.score} ${effective.score.provisional ? styles.scoreProvisional : ''}`} data-testid="score"><div className={styles.scoreNumber}><strong>{effective.score.total === null ? '—' : effective.score.total}</strong><span>{effective.score.total === null ? 'No numeric grade recorded' : 'out of 100 points'}</span></div>
        <div className={styles.scoreInfo}><b>{effective.score.provisional ? effective.score.total === null ? 'Assessment requires review' : 'Provisional assessment' : assessment?.conditional ? 'Conditional result' : effective.source === 'human_review' ? 'Human-reviewed' : 'Saved AI assessment'}</b>
          <span>{effective.source === 'human_review' ? `Human-reviewed · ${effective.accepted_revisions} accepted revision(s)` : 'Based on the saved checklist'}</span>
          {effective.score.provisional && effective.score.score_bounds.lower !== null && effective.score.score_bounds.upper !== null && <span>Possible score range: {effective.score.score_bounds.lower}–{effective.score.score_bounds.upper}.</span>}
          {reviewCriteria.size > 0 && <span>Review recommended for {reviewCriteria.size} {reviewCriteria.size === 1 ? 'criterion' : 'criteria'}. See the specific information needed below.</span>}
          {effective.source === 'human_review' && <small>Original AI: {job.record?.score?.total ?? 'provisional'} · preserved</small>}
        </div>
      </div>
      {job.record?.review && job.record.review.status !== 'not_required' && <div className={['confirmed', 'adjudicated'].includes(job.record.review.status) ? styles.notice : styles.warning} style={{margin: '10px 0'}}>
        <b>{reviewLabel(job.record.review.status)}</b><p style={{marginBottom: 0}}>{job.record.review.criterion_ids.length} criteria {['confirmed', 'adjudicated'].includes(job.record.review.status) ? 'checked' : 'selected for review'}{job.record.review.changed_criteria.length ? ` · ${job.record.review.changed_criteria.length} decisions revised` : ''}.</p>
        {!!job.record.review.disagreements.length && <details><summary>Review differences</summary><p>{job.record.review.disagreements.map(id => checklist.criteria.find(c => c.id === id)?.title || id).join('; ')}</p></details>}
        {job.record.review.coverage_disagreement && <p>The independent review disagrees about which customer requests were answered. Review the source and request coverage before relying on the result.</p>}
        {job.record.review.reviewer_limitations && Object.keys(job.record.review.reviewer_limitations).length > 0 && <details><summary>Limitations raised by the independent reviewer</summary>{Object.entries(job.record.review.reviewer_limitations).map(([id, note]) => <p key={id}><b>{checklist.criteria.find(c => c.id === id)?.title || id}:</b> {note}</p>)}</details>}
        {job.record.review.error && <details><summary>Review details</summary><p>{job.record.review.error}</p></details>}
      </div>}
      <div className={styles.outcomeGrid}><span><b>{effective.judgments.length}</b> criteria</span><span><b>{effective.judgments.filter(j => j.status === 'not_applicable').length}</b> N/A</span><span><b>{reviewCriteria.size}</b> review recommended</span><span><b>{job.appeals.filter(a => a.status === 'open').length}</b> open appeals</span></div>
      <ReviewPriorities effective={effective} checklist={checklist}/>
      {effective.judgments.map(j => {
        const c = checklist.criteria.find(c => c.id === j.criterion_id)!
        const changed = job.appeals.some(a => a.criterion_id === j.criterion_id && a.status === 'accepted')
        const original = !changed && job.record?.evaluation?.judgments.find(item => item.criterion_id === j.criterion_id)
        const judgmentEvidence = original || j
        const native = job.record?.assessment?.criteria[j.criterion_id]
        const level = c.levels.find(level => level.value === j.answer)
        const contribution = effective.score.contributions.find(item => item.criterion_id === j.criterion_id)
        const customFlag = c.kind === 'flag' && !hasBooleanFlagScale(c)
        const reviewRecommended = j.status === 'needs_review' || !!j.uncertainty?.trim() || reviewCriteria.has(j.criterion_id)
        const concern = reviewRecommended || (j.status === 'scored' && (c.kind === 'flag' ? !customFlag && j.answer === 'yes' : (level?.fraction ?? 0) < Math.max(...c.levels.map(l => l.fraction))))
        const decision = j.status === 'not_applicable' ? 'N/A' : j.status === 'needs_review' ? 'Needs review' : c.kind === 'flag' ? j.answer : j.answer === 'yes' ? 'Yes' : j.answer === 'no' ? 'No' : j.answer

        return <article id={`criterion-${j.criterion_id}`} tabIndex={-1} key={j.criterion_id} className={`${styles.card} ${styles.criterion} ${concern ? styles.criterionConcern : customFlag ? styles.criterionNeutral : j.status === 'scored' ? styles.criterionPass : ''}`} data-testid={`criterion-${j.criterion_id}`}>
          <div className={styles.criterionHeader}><div><h3>{c.title}</h3><small>{changed ? 'Human review' : 'AI assessment'} · {c.kind === 'flag' ? 'Separate flag' : `${c.weight} weight`}{reviewRecommended && j.status === 'scored' ? ' · Review recommended' : ''}</small></div><div className={styles.criterionValue}>{decision}{c.kind !== 'flag' && contribution?.points != null && <small>{Number(contribution.points.toFixed(2))} weighted pts</small>}</div></div>
          {customFlag && j.status === 'scored' && level && <p className={styles.flagMeaning}><span>Configured outcome:</span> {level.description}</p>}
          <p>{j.explanation}</p>{j.uncertainty && <p className={styles.warning}><b>Review recommended: </b>{j.uncertainty}</p>}
          <EvidenceButtons items={judgmentEvidence.evidence} onClick={citedEvidence}/>
          {judgmentEvidence.counterevidence.length > 0 && <><small>Counterevidence</small><EvidenceButtons items={judgmentEvidence.counterevidence} onClick={citedEvidence}/></>}
          <div className={styles.criterionActions}><button disabled={!j.checked_message_ids.length} onClick={() => onEvidence([], j.checked_message_ids)}>Show checked messages</button>
            <button onClick={() => onAppeal(j.criterion_id)}>Appeal this judgment</button></div>
          {native && <details><summary>{changed ? 'Original AI assessment basis' : 'Assessment basis'}{native.review_warnings.length ? ` · ${native.review_warnings.length} review notes` : ''}</summary><p>{basisLabel(native.factual_basis)}</p>
            {native.uses_conditional_reference && <p className={styles.warning}>This decision uses a reference under the selected conditional assessment context.</p>}
            {native.review_warnings.map((warning, n) => <p className={styles.warning} key={n}>{warning}</p>)}
            {referenceButtons(native.reference_evidence)}
            {!!native.factual_dialogue_evidence.length && <><small>Factual dialogue evidence</small><EvidenceButtons items={native.factual_dialogue_evidence} onClick={citedEvidence}/></>}
          </details>}
          <details><summary>Configured rule and original AI audit</summary><p>{c.instruction}</p>
            {job.record?.evaluation?.deductions.filter(d => d.criterion_id === c.id).map((d, i) => <div key={i}><blockquote>{d.rule_quote}</blockquote><p>{d.defect}</p><p>{d.overlap_note}</p></div>)}
            {facts.filter(f => f.criterion_ids.includes(c.id)).map((f, i) => <div className={styles.fact} key={i}
              id={`fact-${facts.indexOf(f)}-${checklist.criteria.indexOf(c)}`} tabIndex={-1}
              data-testid={f.claim_id ? `fact-${f.claim_id}` : undefined}>
              <b>{f.status}</b><p>{f.claim}</p><p>{f.explanation}</p>
              {f.assertion_group_id && (() => {
                const group = job.record?.evaluation?.assertion_groups?.find(g => g.group_id === f.assertion_group_id)
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
      <details className={styles.card}><summary>Customer request coverage · original AI analysis</summary>{job.record?.evaluation?.request_coverage.map((r, i) => {
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
      {job.record?.evaluation?.scope_notes.map((n, i) => <p className={styles.muted} key={i}>{n}</p>)}
      {job.evidence_context && <details className={styles.card}><summary>{job.evidence_context_origin === 'captured_with_request' ? 'Context captured with the assessment request' : 'Reconstructed context for inspection'}</summary>
        {job.evidence_context_origin !== 'captured_with_request' && <p>The saved result has no captured reference context. This view uses the preserved input and current inspection rules; it does not establish which source eligibility information the original model received.</p>}
        <p>Actual date: {job.evidence_context.temporal.occurred_on || 'unknown'} · {job.evidence_context.temporal.origin.replaceAll('_', ' ')}.</p>
        <p>Assessment: {job.evidence_context.assessment.mode.replaceAll('_', ' ')} · {job.evidence_context.assessment.scope || 'scope unknown'} · {job.evidence_context.assessment.as_of || 'date unknown'}</p>
        {job.evidence_context.assessment.pack_id && <p>Source pack: {job.evidence_context.assessment.pack_id} · {job.evidence_context.assessment.pack_sha256}</p>}
        {job.evidence_context.references.map(r => <p key={r.reference_id}>{r.reference_id}: {r.usable ? 'Usable' : `Unavailable — ${r.rejection_reasons.join(', ').replaceAll('_', ' ')}`}</p>)}
      </details>}
      <h2 style={{marginTop: 24}}>Appeals & decisions ({job.appeals.length})</h2>{!job.appeals.length && <p className={styles.muted}>Use “Appeal this judgment” on a criterion to request a review. The original assessment is preserved.</p>}{job.appeals.map(a => <article key={a.id} className={styles.card} data-testid={`appeal-${a.criterion_id}`}>
        <b>{a.criterion_id} · {a.status}</b><p>{a.author}: {a.reason}</p><button onClick={() => onEvidence([], a.message_ids)}>Show appeal evidence</button>
        {a.status === 'open' ? <button onClick={() => onResolve(a)}>Review appeal</button> : <><p>{a.resolution?.reviewer}: {a.resolution?.rationale}</p><p>Before: {a.resolution?.before.answer ?? a.resolution?.before.status} → After: {a.resolution?.after.answer ?? a.resolution?.after.status}</p>
          {a.resolution?.supporting_references?.map(ref => <button key={ref.id} onClick={() => onReference(ref)}>Review source: {ref.id}</button>)}</>}
      </article>)}
      <details className={styles.card}><summary>Original AI JSON & provenance</summary><p>Response: {job.record?.response_id} · Prompt: {job.record?.prompt_version}</p>
        {job.record?.evaluation?.source_citations && <p>Source citations: {Object.keys(job.record.evaluation?.source_citations.selections).length} selections resolved from preserved originals. Quote text comes from the selected sources.</p>}
        <pre>{JSON.stringify(job.record, null, 2)}</pre></details>
    </>}
  </>
}

function hasBooleanFlagScale(criterion: Checklist['criteria'][number]) {
  // Flag fractions are all zero and cannot identify the meaning of a custom value.
  // Only the standard yes/no vocabulary has the existing active/inactive convention.
  return criterion.kind === 'flag' && criterion.levels.length === 2
    && criterion.levels.some(level => level.value === 'yes') && criterion.levels.some(level => level.value === 'no')
}

function ReviewPriorities({effective, checklist}: {effective: NonNullable<JobDetail['effective']>; checklist: Checklist}) {
  const entries = effective.judgments.flatMap(judgment => {
    const criterion = checklist.criteria.find(c => c.id === judgment.criterion_id)
    if (!criterion) return []
    const level = criterion.levels.find(level => level.value === judgment.answer)
    const points = effective.score.contributions.find(c => c.criterion_id === criterion.id)?.points
    const loss = judgment.status === 'scored' && criterion.kind !== 'flag' && level
      ? Math.max(0, criterion.weight * Math.max(...criterion.levels.map(l => l.fraction)) - (points ?? criterion.weight * level.fraction)) : 0
    return [{judgment, criterion, loss}]
  })
  const flags = entries.filter(e => hasBooleanFlagScale(e.criterion) && e.judgment.status === 'scored' && effective.score.flags[e.criterion.id] === 'yes')
  const customFlags = entries.filter(e => e.criterion.kind === 'flag' && !hasBooleanFlagScale(e.criterion) && e.judgment.status === 'scored')
  const reviewCriteria = new Set([...effective.score.unresolved_criteria, ...(effective.score.review_recommended_criteria || [])])
  const unresolved = entries.filter(e => e.judgment.status === 'needs_review' || !!e.judgment.uncertainty?.trim() || reviewCriteria.has(e.criterion.id))
  const deductions = entries.filter(e => e.loss > 0.00001).sort((a, b) => b.loss - a.loss)
  const priorities = [
    ...flags.map(e => ({...e, kind: 'flag', label: `Flagged finding · ${e.judgment.answer}`, reason: e.judgment.explanation})),
    ...customFlags.map(e => ({...e, kind: 'custom-flag', label: `Flag answer: ${e.judgment.answer}`, reason: e.judgment.explanation})),
    ...unresolved.map(e => ({...e, kind: 'review', label: e.judgment.status === 'scored' ? 'Review recommended' : 'Needs review', reason: e.judgment.uncertainty || e.judgment.explanation})),
    ...deductions.slice(0, 3).map(e => ({...e, kind: 'deduction', label: `−${Number(e.loss.toFixed(2))} weighted pts`, reason: e.judgment.explanation})),
  ]
  function inspect(id: string) {
    const target = document.getElementById(`criterion-${id}`)
    target?.scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start'})
    target?.focus({preventScroll: true})
  }
  function excerpt(text: string) {
    const clean = text.replace(/\s+/g, ' ').trim()
    if (clean.length <= 145) return clean
    const cut = clean.slice(0, 145), space = cut.lastIndexOf(' ')
    return cut.slice(0, space > 90 ? space : 145) + '…'
  }
  return <section className={styles.priorities} aria-label="Review priorities">
    <div className={styles.priorityHeading}><Icon name="list" size={16}/><h3>Review priorities</h3><span>Current saved result</span></div>
    {priorities.length ? priorities.map(item => <button key={`${item.kind}-${item.criterion.id}`} className={styles.priorityItem} data-priority={item.kind} onClick={() => inspect(item.criterion.id)}>
      <span className={styles.priorityTitle}><b>{item.criterion.title}</b><small>{item.label}</small></span>
      <span className={styles.priorityReason}>{excerpt(item.reason)}</span>
    </button>) : <p className={styles.priorityClear}>No deductions or criteria recommended for review in this assessment.</p>}
    {deductions.length > 0 && <p className={styles.priorityNote}>Showing {Math.min(3, deductions.length)} of {deductions.length} deductions by weighted point loss, before N/A normalization. Select a finding to inspect its evidence.</p>}
    {(flags.length > 0 || customFlags.length > 0) && <p className={styles.priorityNote}>Flags are separate from the numeric score.{customFlags.length > 0 ? ' Custom flag answers retain their configured meaning; they are not classified as pass or fail.' : ''}</p>}
  </section>
}

function failureTitle(code: string) {
  if (code.includes('budget')) return 'Evaluation allowance reached'
  if (code.includes('credit') || code.includes('quota')) return 'Model provider credits unavailable'
  if (code.includes('invalid_evaluation') || code.includes('validation')) return 'The assessment could not be validated'
  if (code.includes('connection') || code.includes('timeout')) return 'The model provider did not respond'
  if (code.includes('restart') || code.includes('interrupted')) return 'This evaluation was interrupted'
  return 'This evaluation did not complete'
}
function failureAdvice(code: string) {
  if (code.includes('budget')) return 'Check the batch allowance and remaining local limit before retrying. No replacement score has been assigned.'
  if (code.includes('credit') || code.includes('quota')) return 'Check the provider account balance before retrying. Previous results remain available.'
  if (code.includes('invalid_evaluation') || code.includes('validation')) return 'The response did not meet the evidence or result requirements. Review the failure details, then explicitly retry if needed.'
  if (code.includes('connection') || code.includes('timeout')) return 'Check connectivity and provider availability. A retry creates a new attempt and may incur a charge.'
  if (code.includes('restart') || code.includes('interrupted')) return 'The service stopped before this attempt finished. Check its details before making a new billable attempt.'
  return 'No assessment is available from this attempt. Review the details before retrying.'
}

function basisLabel(basis: string) {
  const labels: Record<string, string> = {
    not_required: 'The decision follows from the conversation and checklist; no external factual verification is required.',
    observed_interaction: 'The factual basis is an outcome observed in this conversation.',
    observable_commitment: 'The operator made the stated commitment. This does not establish that a future action has completed.',
    policy_reference: 'Applicable reference material supports the factual basis of this decision.',
    private_record: 'An authoritative system record supports the relevant private account fact.',
    mixed_sources: 'Conversation evidence and applicable reference material jointly support the decision.',
    unverified: 'Material information is missing or unverified. Review is recommended; the recorded grade does not verify the missing information.',
  }
  return labels[basis] || basis.replaceAll('_', ' ')
}
function reviewLabel(status: string) {
  const labels: Record<string, string> = {confirmed: 'Independent review agreed on grades', adjudicated: 'Independent review completed',
    needs_human_review: 'Reviewer attention required', review_failed: 'Independent review could not complete', budget_limited: 'Independent review stopped at its allowance'}
  return labels[status] || status.replaceAll('_', ' ')
}
