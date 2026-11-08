import {useState} from 'react'
import type {JobDetail, JobRow} from './types'
import {api} from './api'
import {date} from './format'
import {scoreNumber} from './scorePresentation'
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
  if (!decision) return 'Нет в чек-листе'
  if (decision.status === 'not_applicable') return 'Не применимо'
  if (decision.status === 'needs_review') return 'Требует пересмотра'
  return decision.answer ?? 'Решение не принято'
}

function resultSource(source: string) {
  return source === 'human_review' ? 'Пересмотрено проверяющим'
    : source === 'prepared_demo' ? 'Заранее подготовленный пример' : 'Автоматическая оценка'
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
    <summary>Сравнить сохранённые оценки</summary>
    <p>Сравните оценки разных версий этого диалога. Новая проверка при этом не запускается.</p>
    {candidatesPending && <p className={styles.muted} role="status">Ищем оценки других версий…</p>}
    {candidatesError && <p className={styles.warning}>Не удалось загрузить другие версии: {candidatesError} <button onClick={() => void loadCandidates()}>Повторить</button></p>}
    {choices.length ? <div className={styles.compareControls}>
      <select aria-label="Оценка для сравнения" value={baseline} disabled={pending} onChange={e => {setBaseline(e.target.value); setResult(undefined); setError('')}}>
        <option value="">Выберите оценку для сравнения</option>{choices.map(j => <option key={j.id} value={j.id}>{date(j.created_at)} · {j.id.slice(0, 7)}{j.conversation_id !== job.conversation_id ? ' · другая версия диалога' : ''}{j.review_revision ? ' · пересмотрено' : ''}</option>)}
      </select>
      <button disabled={!baseline || pending} onClick={async () => {
        setPending(true); setError(''); setResult(undefined)
        try {setResult(await api<Comparison>(`/jobs/${job.id}/compare?baseline=${encodeURIComponent(baseline)}`))}
        catch (e) {setError((e as Error).message)} finally {setPending(false)}
      }}>{pending ? 'Сравниваем…' : 'Сравнить'}</button>
    </div> : !candidatesPending && !candidatesError && <p className={styles.muted}>Для сравнения нужна ещё одна завершённая проверка этого диалога. Подойдут и оценки других версий текста или справочных документов.</p>}
    {error && <p className={styles.error} role="alert">{error}</p>}
    {result && <div data-testid="assessment-comparison">
      <div className={styles.compareScores}><div><span>Для сравнения</span><strong>{result.before_score === null ? 'Нет оценки' : scoreNumber(result.before_score)}</strong>{result.before_provisional && <small>Предварительная оценка</small>}<small>{resultSource(result.before_result_source)}</small></div>
        <div aria-hidden="true">→</div><div><span>Выбранный результат</span><strong>{result.after_score === null ? 'Нет оценки' : scoreNumber(result.after_score)}</strong>{result.after_provisional && <small>Предварительная оценка</small>}<small>{resultSource(result.after_result_source)}</small></div>
        {result.score_delta !== null && <div className={styles.compareDelta}>{result.score_delta > 0 ? '+' : ''}{scoreNumber(result.score_delta)}<small>{result.before_provisional || result.after_provisional ? 'разница предварительных оценок' : 'разница оценок'}</small></div>}
      </div>
      {!result.same_conversation && <p className={styles.warning}>Оценки относятся к разным сохранённым версиям диалога. Прежде чем сравнивать баллы, проверьте, что изменилось в тексте и справочных документах.</p>}
      <p>{result.source_changed ? 'Текст диалога изменён.' : 'Текст диалога не изменился.'} {result.context_changed !== undefined && (result.context_changed ? 'Документы или условия проверки изменены. ' : 'Документы и условия проверки не изменились. ')}{result.checklist_changed ? 'Чек-лист изменён.' : 'Чек-лист не изменился.'}</p>
      <div className={styles.row}><b>Изменённых пунктов: {changed.length}</b><button className={styles.quiet} onClick={() => setShowAll(!showAll)}>{showAll ? 'Только изменения' : 'Все пункты'}</button></div>
      {!shown.length && <p className={styles.muted}>Оценки по пунктам и правила не изменились.</p>}
      {shown.map(c => <div className={styles.compareCriterion} key={c.criterion_id}><div><b>{c.title}</b><span>{c.added ? 'Добавлен' : c.removed ? 'Удалён' : c.rule_changed ? 'Изменено правило' : c.outcome_changed ? 'Изменена оценка' : 'Без изменений'}</span></div>
        <p>{answer(c.before)} <span aria-label="изменилось на">→</span> {answer(c.after)}</p>
        <details><summary>Сравнить обоснования</summary>{c.before && <><small>Обоснование оценки для сравнения</small><p>{c.before.explanation}</p>{c.before.uncertainty && <p className={styles.warning}><b>Замечание к оценке для сравнения: </b>{c.before.uncertainty}</p>}</>}{c.after && <><small>Обоснование выбранной оценки</small><p>{c.after.explanation}</p>{c.after.uncertainty && <p className={styles.warning}><b>Замечание к выбранной оценке: </b>{c.after.uncertainty}</p>}</>}
          <p className={styles.muted}>Взвешенные баллы до исключения неприменимых пунктов: {c.before?.contribution == null ? '—' : scoreNumber(c.before.contribution)} → {c.after?.contribution == null ? '—' : scoreNumber(c.after.contribution)}. Эта разница не равна изменению итоговой оценки.</p>
        </details>
      </div>)}
    </div>}
  </details>
}
