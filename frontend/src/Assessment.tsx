import {referenceTitle} from './CustomReferenceApi'
import type {Appeal, CitationSelection, Evidence, HighlightRange, JobDetail, Reference, ReferenceEvidence} from './types'
import styles from './App.module.css'
import reviewStyles from './Assessment.module.css'
import {date, dollars, terminal} from './format'
import {ScoringHelp} from './ScoringHelp'
import {criterionOutcome, criterionPoints, hasBooleanFlagScale, scoreNumber, scoreTotals} from './scorePresentation'
import {GradeOverview} from './GradeOverview'
import {failureAdvice, failureTitle} from './assessmentFailure'

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
    {items.length > 1 && <button onClick={() => onClick(items)}>Показать сообщения с цитатами</button>}</div>
}

export function Assessment({job, busy, onRetry, onCancel, onEvidence, onReference, onAppeal, onResolve}: {
  job: JobDetail; busy: boolean; onRetry: () => void; onCancel: () => void;
  onEvidence: (e: Evidence[], ids?: string[]) => void; onReference: (ref: Reference, quote?: string, selection?: CitationSelection) => void;
  onAppeal: (id: string) => void; onResolve: (a: Appeal) => void;
}) {
  const effective = job.effective, checklist = job.checklist.content
  const reviewCriteria = new Set([...(effective?.score.unresolved_criteria || []), ...(effective?.score.review_recommended_criteria || []),
    ...(effective?.judgments.filter(j => j.status === 'needs_review' || !!j.uncertainty?.trim()).map(j => j.criterion_id) || [])])
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
  const totals = effective ? scoreTotals(effective.score, checklist, effective.judgments) : null
  const provisional = !!effective?.score.provisional || !!assessment?.conditional
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
    }}>{fact.claim} ({statusLabel(fact.status)})</a> : <span>Ссылка на факт не найдена: {id}</span>
  }
  function referenceButtons(items: ReferenceEvidence[]) {
    return items.map((r, n) => <button key={n} onClick={() => {
      const ref = job.conversation.content.references.find(x => x.id === r.reference_id)
      if (ref) onReference(ref, r.quote, selectedSource(r))
    }}>Источник: {referenceTitle({id: r.reference_id}, job.conversation.metadata)} — {r.quote}</button>)
  }
  return <div className={reviewStyles.assessment}>
    <div className={reviewStyles.topbar}>
      <div className={styles.jobTop}><b className={styles.status} data-status={job.status} data-testid="job-status">{job.is_demo ? 'Учебный разбор' : statusLabel(job.status)}</b></div>
      <details className={`${styles.jobDetails} ${reviewStyles.metadata}`}><summary>Сведения и выгрузка</summary><div className={styles.jobMeta}>
        <span>Создано: {date(job.created_at)}</span>
        <span>Чек-лист: {checklist.title} · {checklist.version}</span>
        {job.record?.usage && <span>Модель: {job.record.model} · {dollars(job.record.usage.estimated_cost_usd)} · Попыток: {job.record.attempt_count} · {scoreNumber(job.record.latency_seconds)} с</span>}
        <a href={`/api/jobs/${job.id}/export`}>Скачать результат и историю пересмотра</a>
        {job.status === 'completed' && !job.is_demo && <button disabled={busy} onClick={onRetry}>Проверить ещё раз</button>}
      </div></details>
    </div>
    {job.record?.demo && <div className={styles.notice} data-testid="prepared-demo"><b>Готовый пример · бесплатно</b><p>Этот учебный разбор подготовлен заранее: модель не вызывалась, API-ключ не нужен. Нажимайте на критерии и цитаты, чтобы разобраться в оценке. Проверку своих данных можно запустить отдельно.</p></div>}
    {!effective && assessment?.conditional && <div className={`${styles.warning} ${reviewStyles.conditional}`} data-testid="conditional-assessment"><b>Результат зависит от допущений</b>
      <p>Использованы сведения по теме «{assessment.scope}» на {assessment.as_of}. Не подтверждено, что они действовали на дату диалога.</p>
      <details><summary>Посмотреть допущения</summary><p>Дата диалога: {job.evidence_context?.temporal.occurred_on || job.conversation.content.occurred_on || 'неизвестна'}.</p>{assessment.rationale && <p>{assessment.rationale}</p>}</details></div>}
    {job.status === 'queued' && <div className={styles.card}><p>Ожидает начала проверки.</p><button onClick={onCancel}>Отменить проверку</button></div>}
    {job.status === 'running' && <div className={styles.card} role="status"><p>Проверяем диалог по выбранному чек-листу…</p><p className={styles.muted}>Можно перейти на другую страницу — проверка продолжится.</p></div>}
    {job.record?.error && <div role="alert" className={styles.error} style={{marginTop: 14}}><b>{failureTitle(job.record.error, job.record.api_error_code)}</b>
      <p>{failureAdvice(job.record.error, job.record.api_error_code)}</p>
      {job.record.budget_required_usd != null && <p>Для запуска нужно не менее {dollars(job.record.budget_required_usd)} доступного лимита; осталось {dollars(job.record.budget_available_usd || 0)}. Это лимит расходов, а не стоимость проверки.</p>}
      <details><summary>Технические сведения</summary>{job.record.error_detail && <p>{job.record.error_detail}</p>}<p>{job.record.error}</p>{job.record.validation_reason && <p>{job.record.validation_reason}</p>}{job.record.repair_skipped && <p>Исправление ответа не запрашивалось: {job.record.repair_skipped}.</p>}</details>
    </div>}
    {terminal.has(job.status) && job.status !== 'completed' && <div className={styles.row} style={{marginTop: 12}}><button disabled={busy} onClick={onRetry}>Повторить проверку</button><span className={styles.muted}>Предыдущие результаты сохранены.</span></div>}
    {effective && <>
      <GradeOverview effective={effective} checklist={checklist} provisional={provisional} reviewCriteria={reviewCriteria} originalTotal={job.record?.score?.total}/>
      {totals && <div className={reviewStyles.gradeMath}>
        {totals.weight <= 0 ? <p>Нет применимых критериев с ненулевым весом — итоговая оценка не рассчитывается.</p>
          : totals.earned === null ? <p>Общая оценка сохранена, но подробный расчёт баллов недоступен.</p>
          : effective.score.total === null ? <p>Пока выставлено {scoreNumber(totals.earned)} из {scoreNumber(totals.weight)} баллов. Итог появится после решения по оставшимся критериям.</p>
          : <><p>Получено <b>{scoreNumber(totals.earned)} из {scoreNumber(totals.weight)} баллов</b> по применимым критериям.</p><span>Пересчёт на 100: {scoreNumber(totals.earned)} ÷ {scoreNumber(totals.weight)} × 100 = {scoreNumber(effective.score.total)}.</span></>}
      </div>}
      {(provisional || reviewCriteria.size > 0) && <div className={reviewStyles.reviewSummary} data-testid={assessment?.conditional ? 'conditional-assessment' : undefined}>
        <p>{reviewCriteria.size > 0 ? `Нужно дополнительно проверить ${criteriaCount(reviewCriteria.size)}.` : effective.score.provisional ? 'Перед использованием оценки уточните отмеченные вопросы.' : ''}{assessment?.conditional ? ' Результат зависит от допущений об исходных данных.' : ''}</p>
        {assessment?.conditional && <details><summary>Посмотреть допущения</summary><p>Использованы сведения по теме «{assessment.scope}» на {assessment.as_of}. Не подтверждено, что они действовали на дату диалога.</p><p>Дата диалога: {job.evidence_context?.temporal.occurred_on || job.conversation.content.occurred_on || 'неизвестна'}.</p>{assessment.rationale && <p>{assessment.rationale}</p>}</details>}
      </div>}
      <ScoringHelp/>
      {job.record?.review && job.record.review.status !== 'not_required' && <div className={['confirmed', 'adjudicated'].includes(job.record.review.status) ? styles.notice : styles.warning} style={{margin: '10px 0'}}>
        <b>{reviewLabel(job.record.review.status)}</b><p style={{marginBottom: 0}}>{['confirmed', 'adjudicated'].includes(job.record.review.status) ? 'Проверено критериев' : 'Критериев на проверке'}: {job.record.review.criterion_ids.length}{job.record.review.changed_criteria.length ? ` · Решений изменено: ${job.record.review.changed_criteria.length}` : ''}.</p>
        {!!job.record.review.disagreements.length && <details><summary>Расхождения в проверках</summary><p>{job.record.review.disagreements.map(id => checklist.criteria.find(c => c.id === id)?.title || id).join('; ')}</p></details>}
        {job.record.review.coverage_disagreement && <p>Повторная проверка дала другой вывод о том, на какие вопросы клиента ответили. Сверьте выводы с исходным диалогом.</p>}
        {job.record.review.reviewer_limitations && Object.keys(job.record.review.reviewer_limitations).length > 0 && <details><summary>Замечания повторной проверки</summary>{Object.entries(job.record.review.reviewer_limitations).map(([id, note]) => <p key={id}><b>{checklist.criteria.find(c => c.id === id)?.title || id}:</b> {note}</p>)}</details>}
        {job.record.review.error && <details><summary>Сведения о проверке</summary><p>{job.record.review.error}</p></details>}
      </div>}
      <div className={reviewStyles.summaryLine}><span>Всего критериев: {effective.judgments.length}</span>{effective.judgments.some(j => j.status === 'not_applicable') && <span>Не применяются: {effective.judgments.filter(j => j.status === 'not_applicable').length}</span>}{job.appeals.some(a => a.status === 'open') && <a href="#review-appeals">Запросов на пересмотр: {job.appeals.filter(a => a.status === 'open').length}</a>}</div>
      {effective.judgments.map(j => {
        const c = checklist.criteria.find(c => c.id === j.criterion_id)!
        const changed = job.appeals.some(a => a.criterion_id === j.criterion_id && a.status === 'accepted')
        const original = !changed && job.record?.evaluation?.judgments.find(item => item.criterion_id === j.criterion_id)
        const judgmentEvidence = original || j
        const native = job.record?.assessment?.criteria[j.criterion_id]
        const level = c.levels.find(level => level.value === j.answer)
        const pointSummary = criterionPoints(c, j, effective.score, totals?.weight || 0)
        const customFlag = c.kind === 'flag' && !hasBooleanFlagScale(c)
        const reviewRecommended = j.status === 'needs_review' || !!j.uncertainty?.trim() || reviewCriteria.has(j.criterion_id)
        const concern = reviewRecommended || (j.status === 'scored' && (c.kind === 'flag' ? !customFlag && j.answer === 'yes' : (level?.fraction ?? 0) < Math.max(...c.levels.map(l => l.fraction))))
        const decision = criterionOutcome(c, j)
        const currentWarnings = native && !changed ? native.review_warnings : []
        const conditionalItem = native && !changed && native.uses_conditional_reference

        return <article id={`criterion-${j.criterion_id}`} tabIndex={-1} key={j.criterion_id} className={`${styles.card} ${styles.criterion} ${reviewStyles.criterion} ${concern ? styles.criterionConcern : customFlag ? styles.criterionNeutral : j.status === 'scored' ? styles.criterionPass : ''}`} data-testid={`criterion-${j.criterion_id}`}>
          <div className={styles.criterionHeader}><div><h3>{c.title}</h3>{(changed || reviewRecommended) && <small>{changed ? 'Проверено специалистом' : 'Требует внимания'}</small>}</div><div className={styles.criterionValue}>{decision}</div></div>
          <div className={reviewStyles.pointSummary}><b>{pointSummary.points}</b><span>{pointSummary.share}</span></div>
          {customFlag && j.status === 'scored' && level && <p className={styles.flagMeaning}><span>Значение:</span> {level.description}</p>}
          {(reviewRecommended || currentWarnings.length > 0 || conditionalItem) && <details className={reviewStyles.uncertainty} data-review-notes="true"><summary>{j.status === 'needs_review' ? 'Нужно решение — посмотреть причины' : 'Что нужно уточнить'}</summary>
            {j.uncertainty && <p>{j.uncertainty}</p>}
            {j.status === 'needs_review' && !j.uncertainty && <p>{j.explanation}</p>}
            {currentWarnings.map((warning, n) => <p key={n}>{warning}</p>)}
            {conditionalItem && <p>Решение опирается на справочные материалы с указанными выше допущениями.</p>}
            {reviewRecommended && !j.uncertainty && j.status !== 'needs_review' && currentWarnings.length === 0 && !conditionalItem && <p>Для этого критерия рекомендована дополнительная проверка. Сопоставьте обоснование с цитатами.</p>}
          </details>}
          <details className={reviewStyles.explanation} data-criterion-details="true"><summary>Обоснование и цитаты</summary>
          <p>{j.explanation}</p>
          {j.status === 'scored' && level && <p className={reviewStyles.ruleMeta}>Условие из чек-листа: {level.description}{c.kind !== 'flag' && <><br/>Начислено {scoreNumber(level.fraction * 100)}% от максимума за критерий.</>}</p>}
          <EvidenceButtons items={judgmentEvidence.evidence} onClick={citedEvidence}/>
          {judgmentEvidence.counterevidence.length > 0 && <><small>Цитаты, которые противоречат выводу</small><EvidenceButtons items={judgmentEvidence.counterevidence} onClick={citedEvidence}/></>}
          <div className={styles.criterionActions}><button disabled={!j.checked_message_ids.length} onClick={() => onEvidence([], j.checked_message_ids)}>Показать проверенные сообщения</button>
            {!job.is_demo && <button onClick={() => onAppeal(j.criterion_id)}>Запросить пересмотр</button>}</div>
          {native && <details><summary>{changed ? 'На чём основана исходная проверка' : 'На чём основано решение'}{native.review_warnings.length ? ` · замечаний: ${native.review_warnings.length}` : ''}</summary><p>{basisLabel(native.factual_basis)}</p>
            {native.uses_conditional_reference && <p className={styles.warning}>Это решение использует справочные материалы с допущениями, указанными для проверки.</p>}
            {changed && native.review_warnings.map((warning, n) => <p className={styles.warning} key={n}>{warning}</p>)}
            {referenceButtons(native.reference_evidence)}
            {!!native.factual_dialogue_evidence.length && <><small>Подтверждающие цитаты</small><EvidenceButtons items={native.factual_dialogue_evidence} onClick={citedEvidence}/></>}
          </details>}
          <details><summary>Правило чек-листа и подробный разбор</summary><p>{c.instruction}</p>
            {job.record?.evaluation?.deductions.filter(d => d.criterion_id === c.id).map((d, i) => <div key={i}><blockquote>{d.rule_quote}</blockquote><p>{d.defect}</p><p>{d.overlap_note}</p></div>)}
            {facts.filter(f => f.criterion_ids.includes(c.id)).map((f, i) => <div className={styles.fact} key={i}
              id={`fact-${facts.indexOf(f)}-${checklist.criteria.indexOf(c)}`} tabIndex={-1}
              data-testid={f.claim_id ? `fact-${f.claim_id}` : undefined}>
              <b>{statusLabel(f.status)}</b><p>{f.claim}</p><p>{f.explanation}</p>
              {f.assertion_group_id && (() => {
                const group = job.record?.evaluation?.assertion_groups?.find(g => g.group_id === f.assertion_group_id)
                return group ? <details><summary>{group.composition === 'all_of'
                  ? `В высказывании отдельно проверены факты: ${group.claim_ids.length}`
                  : 'В высказывании проверен один факт'}</summary>
                  <p>Достоверность каждого факта и его влияние на оценку рассмотрены отдельно.</p>
                  <EvidenceButtons items={group.operator_evidence} onClick={citedEvidence}/>
                  {group.claim_ids.filter(id => id !== f.claim_id).map(id => <p key={id}>Связанный факт: {factReference(id)}</p>)}
                </details> : null
              })()}
              {f.verification_scope && <p>Что проверялось: {statusLabel(f.verification_scope)}</p>}
              <small>Утверждение оператора</small><EvidenceButtons items={f.operator_evidence} onClick={citedEvidence}/>
              {f.dialogue_evidence.length > 0 && <><small>Подтверждения в диалоге</small>
                <p>Границы наблюдения: {f.observation_scope ? statusLabel(f.observation_scope) : 'не указаны'}</p>
                {f.supported_proposition && (f.supported_proposition === f.claim
                  ? <p>Наблюдение относится к этому утверждению.</p>
                  : <p>Что подтверждает наблюдение: {f.supported_proposition}</p>)}
                <EvidenceButtons items={f.dialogue_evidence} onClick={citedEvidence}/></>}
              {!f.dialogue_evidence.length && f.supported_proposition && (f.supported_proposition === f.claim
                ? <p>Подтверждается именно это утверждение.</p>
                : <p>Подтверждаемое утверждение: {f.supported_proposition}</p>)}
              {f.proof && <div data-testid={`proof-${f.claim_id || i}`}>
                <b>{f.proof.relation === 'all_of' ? `Для вывода нужны все основания: ${f.proof.required_premise_ids.length}` : 'Прямое подтверждение из источника'}</b>
                <p>{f.proof.explanation}</p>
                {f.proof.premises.map((p, n) => <div key={p.premise_id} data-testid={`premise-${f.claim_id || i}-${p.premise_id}`}>
                  <p><b>Основание {n + 1}{f.proof?.required_premise_ids.includes(p.premise_id) ? ' · обязательно' : ''}</b></p>
                  {p.depends_on_claim_id ? <p>Связанный факт: {factReference(p.depends_on_claim_id)}. Требуемый статус: {statusLabel(p.required_status || '')}.</p>
                    : <><p>{p.proposition === null ? 'Используется это утверждение.' : p.proposition}</p>
                      <EvidenceButtons items={p.evidence} onClick={citedEvidence}/>
                      {referenceButtons(p.reference_evidence)}
                      {p.rule_evidence.map((r, key) => <div key={key}><small>Правило: {checklist.criteria.find(rule => rule.id === r.criterion_id)?.title || r.criterion_id}</small><blockquote>{r.quote}</blockquote></div>)}
                    </>}
                </div>)}
              </div>}
              {!!f.context_evidence?.length && <><small>Контекст от клиента или системы; не является независимым подтверждением</small>
                <EvidenceButtons items={f.context_evidence} onClick={citedEvidence}/></>}
              {referenceButtons(f.reference_evidence)}
              {f.assessment?.correction && <div><b>Предыдущая рекомендация явно исправлена</b>
                <p>{f.assessment.correction.explanation}</p>
                <p>Оставшиеся последствия: {statusLabel(f.assessment.correction.remaining_consequence)}</p>
                <small>Исправление</small><EvidenceButtons items={f.assessment.correction.operator_evidence} onClick={citedEvidence}/>
                <small>Независимые подтверждения результата</small><EvidenceButtons items={f.assessment.correction.outcome_evidence} onClick={citedEvidence}/>
                {referenceButtons(f.assessment.correction.reference_evidence)}
              </div>}
              {f.assessment?.impacts.filter(impact => impact.criterion_id === c.id).map(impact => <div key={impact.criterion_id}>
                <p>Если факт верен: <b>{criterionOutcome(c, impact.when_true)}{impact.when_true.answer !== null && ` (ответ: ${impact.when_true.answer})`}</b>. Если неверен: <b>{criterionOutcome(c, impact.when_false)}{impact.when_false.answer !== null && ` (ответ: ${impact.when_false.answer})`}</b>.</p>
                <p>{impact.explanation}</p>
                {impact.fixed_claim_ids && <><small>Другие факты, принятые неизменными для сравнения</small>
                  {impact.fixed_claim_ids.length ? <ul>{impact.fixed_claim_ids.map(id => <li key={id}>{factReference(id)}</li>)}</ul>
                    : <p>Другие связанные факты не указаны.</p>}</>}
              </div>)}
            </div>)}
            {changed && <p>Этот разбор относится к исходному автоматическому результату. Решение специалиста сохранено ниже.</p>}
          </details>
          </details>
        </article>
      })}
      {!!job.record?.evaluation?.request_coverage.length && <details className={`${styles.card} ${reviewStyles.secondary}`}><summary>На все ли вопросы клиента ответили?</summary>{job.record?.evaluation?.request_coverage.map((r, i) => {
        const support = r.support, omission = support?.omission
        const interval = omission ? omissionRange(omission.start_message_id, omission.end_message_id) : []
        return <div key={i}><b>{statusLabel(r.status)}: {r.request}</b><p>{r.explanation}</p>
          <button onClick={() => onEvidence([], [...r.request_message_ids, ...r.answer_message_ids])}>Показать вопрос и ответы</button>
          {support && <>
            {support.basis === 'none' ? <p>Ответ оператора не найден.</p> : <><p>{support.basis === 'withdrawn' ? 'Подтверждение того, что клиент снял вопрос' : `Подтверждение ответа оператора: ${statusLabel(support.basis)}`}</p>
              <EvidenceButtons items={support.evidence} onClick={citedEvidence}/></>}
            {support.inference && <p>Как сделан вывод об ответе: {support.inference}</p>}
            {support.unresolved_aspects.length > 0 && <p>Осталось без ответа: {support.unresolved_aspects.join('; ')}</p>}
          </>}
          {omission && <div><p>Проверенный участок диалога: {omission.start_message_id}–{omission.end_message_id}</p>
            <button disabled={!interval.length} onClick={() => onEvidence([], interval)}>Показать весь проверенный участок</button>
            <p>Контекст пропущенного ответа; не подтверждает, что оператор ответил</p><EvidenceButtons items={omission.context_evidence} onClick={citedEvidence}/>
          </div>}
        </div>
      })}</details>}
      {job.record?.evaluation?.scope_notes.map((n, i) => <p className={styles.muted} key={i}>{n}</p>)}
      {job.evidence_context && <details className={`${styles.card} ${reviewStyles.secondary}`}><summary>Источники и даты</summary>
        {job.evidence_context_origin !== 'captured_with_request' && <p>В сохранённом результате нет сведений о том, какие источники были доступны при проверке. Здесь показаны исходные данные по текущим правилам просмотра; они не подтверждают, что именно было передано модели.</p>}
        <p>Дата диалога: {job.evidence_context.temporal.occurred_on || 'неизвестна'} · {dateOriginLabel(job.evidence_context.temporal.origin)}.</p>
        <p>Режим проверки: {job.evidence_context.assessment.mode === 'snapshot_review' ? 'По сведениям на выбранную дату' : 'На дату диалога'} · {job.evidence_context.assessment.scope || 'область не указана'} · {job.evidence_context.assessment.as_of || 'дата неизвестна'}</p>
        {job.evidence_context.assessment.pack_id && <p>Набор источников: {job.evidence_context.assessment.pack_id} · {job.evidence_context.assessment.pack_sha256}</p>}
        {job.evidence_context.references.map(r => <p key={r.reference_id}>{r.reference_id}: {r.usable ? 'Применим' : `Не применим: ${r.rejection_reasons.map(referenceReason).join('; ')}`}</p>)}
      </details>}
      {job.appeals.length > 0 && <h2 id="review-appeals" className={reviewStyles.appealsHeading}>Запросы на пересмотр ({job.appeals.length})</h2>}{job.appeals.map(a => <article key={a.id} className={styles.card} data-testid={`appeal-${a.criterion_id}`}>
        <b>{checklist.criteria.find(c => c.id === a.criterion_id)?.title || a.criterion_id} · {statusLabel(a.status)}</b><p>{a.author}: {a.reason}</p><button onClick={() => onEvidence([], a.message_ids)}>Показать выбранные сообщения</button>
        {a.status === 'open' ? <button onClick={() => onResolve(a)}>Рассмотреть запрос</button> : <><p>{a.resolution?.reviewer}: {a.resolution?.rationale}</p><p>Было: {a.resolution?.before.answer ?? statusLabel(a.resolution?.before.status || '')} → Стало: {a.resolution?.after.answer ?? statusLabel(a.resolution?.after.status || '')}</p>
          {a.resolution?.supporting_references?.map(ref => <button key={ref.id} onClick={() => onReference(ref)}>Источник решения: {ref.id}</button>)}</>}
      </article>)}
      <details className={`${styles.card} ${reviewStyles.secondary}`}><summary>Техническая запись</summary><p>Ответ модели: {job.record?.response_id} · Версия инструкции: {job.record?.prompt_version}</p>
        {job.record?.evaluation?.source_citations && <p>Цитат из сохранённых оригиналов: {Object.keys(job.record.evaluation?.source_citations.selections).length}. Текст цитат взят из выбранных источников.</p>}
        <pre>{JSON.stringify(job.record, null, 2)}</pre></details>
    </>}
  </div>
}

function basisLabel(basis: string) {
  const labels: Record<string, string> = {
    not_required: 'Решение следует из диалога и чек-листа. Проверка по внешним источникам не требуется.',
    observed_interaction: 'Решение основано на результате, который виден в диалоге.',
    observable_commitment: 'Оператор дал указанное обещание. Это не подтверждает, что обещанное действие уже выполнено.',
    policy_reference: 'Решение подтверждается применимыми справочными материалами.',
    private_record: 'Факт о клиентском счёте подтверждается достоверной системной записью.',
    mixed_sources: 'Решение подтверждается диалогом и применимыми справочными материалами.',
    unverified: 'Существенные сведения отсутствуют или не проверены. Нужна дополнительная проверка; выставленная оценка не подтверждает недостающие сведения.',
  }
  return labels[basis] || 'Основание не указано.'
}
function reviewLabel(status: string) {
  const labels: Record<string, string> = {confirmed: 'Повторная проверка подтвердила оценки', adjudicated: 'Повторная проверка завершена',
    needs_human_review: 'Нужна проверка специалиста', review_failed: 'Повторную проверку не удалось завершить', budget_limited: 'Повторная проверка остановлена из-за лимита'}
  return labels[status] || 'Статус повторной проверки не указан'
}

function criteriaCount(count: number) {
  const ending = count % 100 >= 11 && count % 100 <= 14 ? 'критериев' : count % 10 === 1 ? 'критерий' : count % 10 >= 2 && count % 10 <= 4 ? 'критерия' : 'критериев'
  return `${count} ${ending}`
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    completed: 'Проверка завершена', failed: 'Не удалось завершить', queued: 'В очереди', running: 'Выполняется проверка',
    cancelled: 'Отменено', interrupted: 'Прервано', scored: 'Оценено', not_applicable: 'Не применяется', needs_review: 'Нужно решение',
    supported: 'Подтверждено', contradicted: 'Опровергнуто', unverified: 'Не подтверждено',
    answered: 'Ответ получен', partial: 'Ответ частичный', unanswered: 'Без ответа', next_step: 'Предложен следующий шаг', withdrawn: 'Клиент снял вопрос',
    explicit: 'Прямой ответ', implied: 'Ответ следует из контекста', none: 'Не указано',
    reported_state: 'Сообщение о состоянии', control_visible: 'Элемент интерфейса виден', action_completed: 'Действие выполнено',
    task_completed: 'Задача выполнена', system_record: 'Системная запись', interaction: 'Ход диалога', policy: 'Правила и условия',
    private_record: 'Клиентские данные', grading_rule: 'Правило оценки', commitment: 'Обещание оператора',
    none_established: 'Не установлены', present: 'Сохраняются', uncertain: 'Неясны',
    open: 'Ожидает решения', accepted: 'Пересмотр принят', rejected: 'Пересмотр отклонён',
  }
  return labels[status] || 'Статус не указан'
}

function dateOriginLabel(origin: string) {
  const labels: Record<string, string> = {explicit: 'Указана в исходных данных', iso_timestamp_consensus: 'Определена по времени сообщений', conflict: 'В датах есть противоречия', unavailable: 'Не удалось определить по сообщениям'}
  return labels[origin] || 'Источник даты не указан'
}

function referenceReason(reason: string) {
  const labels: Record<string, string> = {
    reference_context_scope_mismatch: 'тема не совпадает с выбранным контекстом', reference_context_scope_unconfirmed: 'тема выбранного контекста не подтверждена',
    missing_scope: 'не указана область применения', scope_mismatch: 'не совпадает область применения', source_date_conflict: 'даты источников противоречат друг другу',
    missing_assessment_date: 'не указана дата проверки', missing_occurrence_date: 'неизвестна дата диалога', snapshot_date_mismatch: 'не совпадает дата сведений',
    before_validity_window: 'диалог состоялся до начала действия источника', after_validity_window: 'на дату диалога источник уже не действовал',
  }
  return labels[reason] || 'требуется уточнить применимость источника'
}
