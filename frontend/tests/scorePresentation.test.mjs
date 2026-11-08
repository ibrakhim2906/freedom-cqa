import test from 'node:test'
import assert from 'node:assert/strict'
import {criterionOutcome, criterionPoints, scoreTotals} from '../src/scorePresentation.ts'

const criterion = {id: 'care', title: 'Care', kind: 'scale', weight: 20,
  levels: [{value: '20', fraction: 1, description: 'Complete'}, {value: '10', fraction: .5, description: 'Partial'}]}
const judgment = {criterion_id: 'care', status: 'scored', answer: '10', uncertainty: null}
const score = {total: 50, contributions: [{criterion_id: 'care', status: 'scored', points: 10}]}

test('numeric answer IDs become a human outcome; awarded points come from saved contributions', () => {
  assert.equal(criterionOutcome(criterion, judgment), 'Часть баллов')
  assert.equal(criterionPoints(criterion, judgment, score, 40).points, 'Получено 10 из 20 баллов')
  assert.equal(criterionPoints(criterion, judgment, score, 40).share, 'Вклад в итоговую оценку: 25 из 100')
  const custom = {...criterion, levels: [{value: '999', fraction: .5, description: 'Partial'}]}
  assert.equal(criterionOutcome(custom, {...judgment, answer: '999'}), 'Часть баллов')
  assert.equal(criterionPoints(custom, judgment, {...score, contributions: []}, 20).points, 'Данные о баллах не сохранены')
})

test('earned contribution uses the applicable denominator after exclusions, not the maximum criterion weight', () => {
  assert.deepEqual(criterionPoints(criterion, judgment, {...score, total: 87.5, applicable_weight: 80}, 80), {
    points: 'Получено 10 из 20 баллов', share: 'Вклад в итоговую оценку: 12,5 из 100',
  })
  const zeroEarned = {...score, contributions: [{criterion_id: 'care', status: 'scored', points: 0}]}
  assert.equal(criterionPoints(criterion, {...judgment, answer: '0'}, zeroEarned, 80).share,
    'Вклад в итоговую оценку: 0 из 100')
})

test('pending and missing historical points do not fabricate an earned contribution', () => {
  assert.equal(criterionPoints(criterion, {...judgment, status: 'needs_review', answer: null}, score, 80).share,
    'Вклад будет рассчитан после оценки критерия')
  for (const contributions of [[], [{criterion_id: 'care', status: 'scored', points: null}]]) {
    assert.equal(criterionPoints(criterion, judgment, {...score, contributions}, 80).share,
      'Вклад не рассчитан: нет сохранённых баллов')
  }
  assert.equal(criterionPoints(criterion, judgment, score, 0).share, 'Недостаточно данных для пересчёта на 100')
  assert.equal(criterionPoints({...criterion, weight: 0}, judgment, score, 0).share,
    'Критерий без баллов — на оценку не влияет')
})

test('uncertain and incomplete results label their earned contribution as provisional', () => {
  assert.equal(criterionPoints(criterion, judgment, {...score, provisional: true}, 80).share,
    'Предварительный вклад: 12,5 из 100')
  assert.equal(criterionPoints(criterion, judgment, {...score, total: null}, 80).share,
    'Предварительный вклад: 12,5 из 100')
  assert.equal(criterionPoints(criterion, {...judgment, uncertainty: 'Дата требует уточнения'}, score, 80).share,
    'Предварительный вклад: 12,5 из 100')
})

test('custom textual outcomes and flag meanings are preserved without treating flags as scoring', () => {
  assert.equal(criterionOutcome(criterion, {...judgment, answer: 'Спокойно и вежливо'}), 'Спокойно и вежливо')
  const flag = {...criterion, kind: 'flag', weight: 0, levels: [{value: '2', fraction: 0, description: 'Requires follow-up'}]}
  assert.equal(criterionOutcome(flag, {...judgment, answer: '2'}), 'Отдельная отметка')
  assert.equal(criterionPoints(flag, judgment, score, 20).points, 'На итоговую оценку не влияет')
})

test('not applicable and unresolved are not presented as zero earned', () => {
  assert.deepEqual(criterionPoints(criterion, {...judgment, status: 'not_applicable'}, score, 20), {
    points: 'Не входит в итоговую оценку', share: '20 баллов исключено из расчёта',
  })
  assert.equal(criterionPoints(criterion, {...judgment, status: 'needs_review'}, score, 20).points, 'Баллы пока не выставлены')
  assert.equal(criterionPoints({...criterion, weight: 0}, judgment, {...score, contributions: [{criterion_id: 'care', points: 0}]}, 0).points, 'Получено 0 из 0 баллов')
})

test('actual aggregate fields take precedence; historical fallback excludes N/A and flags', () => {
  const checklist = {criteria: [criterion, {...criterion, id: 'na', weight: 50}, {...criterion, id: 'flag', kind: 'flag', weight: 0}]}
  const judgments = [judgment, {...judgment, criterion_id: 'na', status: 'not_applicable'}, {...judgment, criterion_id: 'flag'}]
  assert.deepEqual(scoreTotals(score, checklist, judgments), {weight: 20, earned: 10})
  assert.deepEqual(scoreTotals({...score, earned_points: 12, applicable_weight: 25}, checklist, judgments), {weight: 25, earned: 12})
  assert.deepEqual(scoreTotals({...score, contributions: []}, checklist, judgments), {weight: 20, earned: null})
})

test('zero weight unresolved items retain pending state without affecting the denominator', () => {
  const zero = {...criterion, id: 'zero', weight: 0}
  const pending = {...judgment, criterion_id: 'zero', status: 'needs_review', answer: null}
  assert.deepEqual(scoreTotals(score, {criteria: [criterion, zero]}, [judgment, pending]), {weight: 20, earned: 10})
  assert.equal(criterionPoints(zero, pending, score, 20).points, 'Баллы пока не выставлены')
})
