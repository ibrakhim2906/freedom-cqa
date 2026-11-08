import type {Checklist, Criterion} from './types'

export const answerLabel = (value: string) => value === 'yes' ? 'Да' : value === 'no' ? 'Нет' : value
const labelKey = (value: string) => answerLabel(value).trim().toLocaleLowerCase('ru-RU')

export function instructionLines(text: string) {
  // Keep the trailing empty line while typing; otherwise Enter disappears.
  return text.split('\n')
}

export function nextAnswerValue(levels: Criterion['levels']) {
  const used = new Set(levels.map(level => labelKey(level.value)))
  let number = levels.length + 1
  while (used.has(labelKey(`Вариант ${number}`))) number++
  return `Вариант ${number}`
}

export type ChecklistIssue = {field: string; message: string; criterionIndex?: number}

export function checklistIssues(checklist: Checklist): ChecklistIssue[] {
  const issues: ChecklistIssue[] = []
  const add = (field: string, message: string, criterionIndex?: number) => issues.push({field, message, criterionIndex})
  if (!checklist.title.trim()) add('title', 'Укажите название чек-листа.')
  if (!checklist.id.trim()) add('id', 'Укажите идентификатор чек-листа в технических сведениях.')
  if (!checklist.version.trim()) add('version', 'Укажите версию чек-листа в технических сведениях.')
  if (!checklist.criteria.length) add('criteria', 'Добавьте хотя бы один критерий.')
  const ids = new Set<string>()
  checklist.criteria.forEach((criterion, i) => {
    const prefix = `criterion-${i}`, name = `Критерий ${i + 1}`
    if (!criterion.id.trim()) add(`${prefix}-id`, `${name}: укажите идентификатор в технических сведениях.`, i)
    else if (ids.has(criterion.id.trim())) add(`${prefix}-id`, `${name}: идентификатор уже используется другим критерием.`, i)
    ids.add(criterion.id.trim())
    if (!criterion.title.trim()) add(`${prefix}-title`, `${name}: укажите название.`, i)
    if (!criterion.instruction.trim()) add(`${prefix}-instruction`, `${name}: опишите правило оценки.`, i)
    if (!Number.isFinite(criterion.weight) || criterion.weight < 0) add(`${prefix}-weight`, `${name}: максимум баллов должен быть числом не меньше нуля.`, i)
    if (criterion.kind === 'flag' && criterion.weight !== 0) add(`${prefix}-weight`, `${name}: отдельная отметка должна иметь максимум 0 баллов.`, i)
    if (!criterion.levels.length) add(`${prefix}-levels`, `${name}: добавьте хотя бы один вариант ответа.`, i)
    const labels = new Set<string>()
    criterion.levels.forEach((level, n) => {
      const field = `${prefix}-answer-${n}`, label = labelKey(level.value)
      if (!label) add(`${field}-value`, `${name}, ответ ${n + 1}: укажите название.`, i)
      else if (labels.has(label)) add(`${field}-value`, `${name}, ответ ${n + 1}: название «${answerLabel(level.value).trim()}» уже используется. Выберите другое.`, i)
      labels.add(label)
      if (!level.description.trim()) add(`${field}-description`, `${name}, ответ ${n + 1}: опишите, когда его выбирать.`, i)
      if (!Number.isFinite(level.fraction) || level.fraction < 0 || level.fraction > 1) add(`${field}-fraction`, `${name}, ответ ${n + 1}: баллы должны быть от 0 до максимума за критерий.`, i)
    })
  })
  return issues
}
