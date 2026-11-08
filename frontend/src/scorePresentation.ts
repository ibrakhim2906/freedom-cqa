import type {Checklist, Criterion, Judgment, Score} from './types'

export function scoreNumber(value: number) {
  return value !== 0 && Math.abs(value) < 0.00000001
    ? value.toExponential(2).replace('.', ',')
    : new Intl.NumberFormat('ru-RU', {maximumFractionDigits: 8}).format(value)
}

export function scorePoints(value: number) {
  const form = new Intl.PluralRules('ru-RU', {maximumFractionDigits: 20}).select(value)
  return `${scoreNumber(value)} ${form === 'one' ? 'балл' : form === 'few' || form === 'other' ? 'балла' : 'баллов'}`
}

export function hasBooleanFlagScale(criterion: Criterion) {
  // Custom flags cannot be interpreted from their credit fractions.
  return criterion.kind === 'flag' && criterion.levels.length === 2
    && criterion.levels.some(level => level.value === 'yes') && criterion.levels.some(level => level.value === 'no')
}

function numericAnswer(value: string) {
  return /^[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:e[+-]?\d+)?\s*%?$/i.test(value.trim())
}

export function criterionOutcome(criterion: Criterion, judgment: Pick<Judgment, 'status'|'answer'>) {
  if (judgment.status === 'not_applicable') return 'Не применяется'
  if (judgment.status === 'needs_review') return 'Нужно решение'
  const level = criterion.levels.find(item => item.value === judgment.answer)
  if (criterion.kind === 'flag') {
    if (hasBooleanFlagScale(criterion)) return judgment.answer === 'yes' ? 'Отмечено' : 'Не отмечено'
    return judgment.answer && !numericAnswer(judgment.answer) ? judgment.answer : 'Отдельная отметка'
  }
  if (judgment.answer === 'yes') return 'Да'
  if (judgment.answer === 'no') return 'Нет'
  if (judgment.answer && !numericAnswer(judgment.answer)) return judgment.answer
  if (!level) return 'Результат сохранён'
  return level.fraction === 1 ? 'Полный балл' : level.fraction === 0 ? 'Без баллов' : 'Часть баллов'
}

export function scoreTotals(score: Score, checklist: Checklist, judgments: Judgment[]) {
  const applicable = checklist.criteria.filter(item => item.kind !== 'flag'
    && judgments.some(j => j.criterion_id === item.id && j.status !== 'not_applicable'))
  const scored = applicable.filter(item => judgments.some(j => j.criterion_id === item.id && j.status === 'scored'))
  const contributions = scored.map(item => score.contributions.find(c => c.criterion_id === item.id)?.points)
  return {
    weight: score.applicable_weight ?? applicable.reduce((sum, item) => sum + item.weight, 0),
    // Older records may omit aggregate fields. Use saved contributions, never
    // infer awarded points from the answer label or regenerate a model result.
    earned: score.earned_points ?? (contributions.every(p => p != null)
      ? contributions.reduce<number>((sum, points) => sum + (points ?? 0), 0) : null),
  }
}

export function criterionPoints(criterion: Criterion, judgment: Judgment, score: Score, applicableWeight: number) {
  if (criterion.kind === 'flag') return {points: 'На итоговую оценку не влияет', share: 'Отдельная отметка'}
  if (judgment.status === 'not_applicable') return {
    points: 'Не входит в итоговую оценку', share: `${scoreNumber(criterion.weight)} баллов исключено из расчёта`,
  }
  const contribution = score.contributions.find(item => item.criterion_id === criterion.id)
  const points = judgment.status !== 'scored' ? 'Баллы пока не выставлены'
    : contribution?.points == null ? 'Данные о баллах не сохранены'
    : `Получено ${scoreNumber(contribution.points)} из ${scoreNumber(criterion.weight)} баллов`
  // Normalize awarded points, not the criterion's maximum. A pending decision
  // or missing historical contribution must never look like an earned zero.
  const provisional = score.provisional || score.total === null || !!judgment.uncertainty
  const share = criterion.weight === 0 ? 'Критерий без баллов — на оценку не влияет'
    : judgment.status !== 'scored' ? 'Вклад будет рассчитан после оценки критерия'
    : contribution?.points == null || !Number.isFinite(contribution.points) ? 'Вклад не рассчитан: нет сохранённых баллов'
    : !Number.isFinite(applicableWeight) || applicableWeight <= 0 ? 'Недостаточно данных для пересчёта на 100'
    : `${provisional ? 'Предварительный вклад' : 'Вклад в итоговую оценку'}: ${scoreNumber(contribution.points / applicableWeight * 100)} из 100`
  return {points, share}
}
