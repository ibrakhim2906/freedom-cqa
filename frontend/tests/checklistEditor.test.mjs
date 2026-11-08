import test from 'node:test'
import assert from 'node:assert/strict'
import {answerLabel, checklistIssues, instructionLines, nextAnswerValue} from '../src/checklistEditor.ts'

const criterion = () => ({id: 'contact', title: 'Приветствие', instruction: 'Оператор представился.', kind: 'binary', weight: 10,
  levels: [{value: 'yes', fraction: 1, description: 'Представился'}, {value: 'no', fraction: 0, description: 'Не представился'}],
  na_condition: null, channel_guidance: {}})
const checklist = () => ({id: 'my-checklist', title: 'Мой чек-лист', version: '1', instructions: [], criteria: [criterion()]})

test('sequential typing keeps Enter and blank lines in general instructions', () => {
  let lines = []
  for (const character of 'Оценивайте оператора.\n\nУчитывайте весь диалог.\n') {
    lines = instructionLines(lines.join('\n') + character)
  }
  assert.deepEqual(lines, ['Оценивайте оператора.', '', 'Учитывайте весь диалог.', ''])
})

test('adding after deleting a middle answer generates a unique visible name', () => {
  const levels = criterion().levels
  levels.push({value: nextAnswerValue(levels), fraction: 0.5, description: 'Частично'})
  levels.push({value: nextAnswerValue(levels), fraction: 0.5, description: 'Почти полностью'})
  levels.splice(2, 1)
  assert.equal(nextAnswerValue(levels), 'Вариант 5')
  levels.push({value: ' вариант 5 ', fraction: 0.5, description: 'Ещё один'})
  assert.equal(nextAnswerValue(levels), 'Вариант 6')
})

test('duplicate names are caught using the labels the user actually sees', () => {
  const value = checklist()
  value.criteria[0].levels.push({value: ' да ', fraction: 0.5, description: 'Другой ответ'})
  const issues = checklistIssues(value)
  assert.equal(answerLabel('yes'), 'Да')
  assert.deepEqual(issues.map(issue => issue.field), ['criterion-0-answer-2-value'])
  assert.match(issues[0].message, /уже используется/)
  assert.equal(issues[0].criterionIndex, 0)
})

test('errors identify empty criteria and answers before save', () => {
  const value = checklist()
  value.criteria[0].instruction = ' '
  value.criteria[0].levels = []
  assert.deepEqual(checklistIssues(value).map(issue => issue.field), ['criterion-0-instruction', 'criterion-0-levels'])
  value.criteria = []
  assert.deepEqual(checklistIssues(value).map(issue => issue.field), ['criteria'])
})

test('validation preserves valid zero scores, tiny weights and nullable exceptions without mutation', () => {
  const value = checklist()
  value.criteria[0].weight = 1e-9
  value.criteria.push({...criterion(), id: 'flag', kind: 'flag', weight: 0})
  value.instructions = ['Первая строка', '', 'Вторая строка', '']
  const before = structuredClone(value)
  assert.deepEqual(checklistIssues(value), [])
  assert.deepEqual(value, before)
})

test('invalid numeric points and duplicate criterion identifiers identify their fields', () => {
  const value = checklist()
  value.criteria[0].levels[0].fraction = 1.1
  value.criteria.push(criterion())
  value.criteria[1].weight = Number.NaN
  assert.deepEqual(checklistIssues(value).map(issue => issue.field), ['criterion-0-answer-0-fraction', 'criterion-1-id', 'criterion-1-weight'])
})
