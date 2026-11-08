import {useId, useRef, useState} from 'react'
import type {Checklist, Criterion} from './types'
import styles from './App.module.css'
import editorStyles from './Checklists.module.css'
import {ScoringHelp} from './ScoringHelp'
import {scoreNumber, scorePoints} from './scorePresentation'
import {answerLabel, checklistIssues, instructionLines, nextAnswerValue, type ChecklistIssue} from './checklistEditor'

export function newCriterion(): Criterion {
  return {id: `criterion-${crypto.randomUUID()}`, title: 'Новый критерий', instruction: '', kind: 'binary', weight: 10,
    na_condition: null, channel_guidance: {}, levels: [{value: 'yes', fraction: 1, description: 'Требование выполнено.'}, {value: 'no', fraction: 0, description: 'Требование не выполнено.'}]}
}
export function ChecklistEditor({value, onChange, onSave, busy}: {value: Checklist; onChange: (c: Checklist) => void; onSave: () => void; busy: boolean}) {
  const [submitted, setSubmitted] = useState(false)
  const [expanded, setExpanded] = useState<number[]>(value.criteria.length === 1 ? [0] : [])
  const form = useRef<HTMLFormElement>(null), errorId = useId()
  const issues = submitted ? checklistIssues(value) : []
  const fieldProps = (field: string) => {
    const index = issues.findIndex(issue => issue.field === field)
    return {'data-field': field, 'aria-invalid': index >= 0 || undefined, 'aria-describedby': index >= 0 ? `${errorId}-${index}` : undefined}
  }
  const showIssue = (issue: ChecklistIssue) => {
    if (issue.criterionIndex !== undefined) setExpanded(old => [...new Set([...old, issue.criterionIndex!])])
    requestAnimationFrame(() => {
      const control = form.current?.querySelector<HTMLElement>(`[data-field="${issue.field}"]`)
      for (let parent = control?.parentElement; parent; parent = parent.parentElement) {
        if (parent instanceof HTMLDetailsElement) parent.open = true
      }
      control?.focus()
    })
  }
  const change = (i: number, patch: Partial<Criterion>) => onChange({...value, criteria: value.criteria.map((c, n) => n === i ? {...c, ...patch} : c)})
  const addItem = () => {setExpanded(old => [...old, value.criteria.length]); onChange({...value, criteria: [...value.criteria, newCriterion()]})}
  const removeItem = (index: number) => {
    setExpanded(old => old.filter(i => i !== index).map(i => i > index ? i - 1 : i))
    onChange({...value, criteria: value.criteria.filter((_, i) => i !== index)})
  }
  const scoringWeight = value.criteria.filter(c => c.kind !== 'flag').reduce((total, c) => total + c.weight, 0)
  return <form ref={form} className={editorStyles.editor} noValidate onSubmit={event => {
    event.preventDefault(); setSubmitted(true)
    const problems = checklistIssues(value)
    if (problems.length) {showIssue(problems[0]); return}
    onSave()
  }}>
    <div className={editorStyles.actions}><div><b>Критериев: {value.criteria.length}</b><span>Сохраните чек-лист, чтобы использовать его при проверке.</span></div><button className={styles.primary} type="submit" disabled={busy}>{busy ? 'Сохранение…' : 'Сохранить чек-лист'}</button></div>
    {!!issues.length && <div className={editorStyles.validation} role="alert"><b>Перед сохранением исправьте следующие поля:</b><ul>{issues.map((issue, i) => <li id={`${errorId}-${i}`} key={`${issue.field}-${i}`}><button type="button" onClick={() => showIssue(issue)}>{issue.message}</button></li>)}</ul></div>}
    <div className={`${editorStyles.twoColumns} ${editorStyles.basics}`}>
      <label className={editorStyles.name}>Название чек-листа<input {...fieldProps('title')} aria-label="Название чек-листа" required value={value.title} onChange={e => onChange({...value, title: e.target.value})} placeholder="Например, Качество клиентской поддержки"/></label>
      <label><span>Общие указания <span className={editorStyles.optional}>Необязательно</span></span><textarea rows={3} aria-label="Общие указания — по одному на строке" value={value.instructions.join('\n')} onChange={e => onChange({...value, instructions: instructionLines(e.target.value)})} placeholder="Например, оценивайте только ответы оператора."/></label>
    </div>
    <p className={editorStyles.scoringWeight}>За полное выполнение всех критериев: <b>{scorePoints(scoringWeight)}</b>. Отметки без баллов в расчёт не входят.</p>
    {scoringWeight <= 0 && <p className={editorStyles.scoringWarning} role="status">По этому чек-листу нельзя рассчитать итоговую оценку. Укажите число баллов больше нуля хотя бы для одного критерия.</p>}
    <ScoringHelp/>
    <details className={editorStyles.technical}><summary>Технические сведения</summary><p>Идентификаторы заполняются автоматически. Менять их нужно только для совместимости с внешней системой.</p><div className={editorStyles.twoColumns}><label>ID чек-листа<input {...fieldProps('id')} value={value.id} required onChange={e => onChange({...value, id: e.target.value})}/></label><label>Версия<input {...fieldProps('version')} required value={value.version} onChange={e => onChange({...value, version: e.target.value})}/></label></div></details>
    <div className={editorStyles.sectionHeading}><div><h3>Что должен сделать оператор?</h3><p>Откройте критерий, чтобы изменить правило или баллы.</p></div><button {...fieldProps('criteria')} type="button" onClick={addItem}>Добавить критерий</button></div>
    {value.criteria.map((c, i) => <details className={editorStyles.criterion} key={i} open={expanded.includes(i)} onToggle={event => {
      const open = event.currentTarget.open
      setExpanded(old => open === old.includes(i) ? old : open ? [...old, i] : old.filter(index => index !== i))
    }}>
      <summary><span>{i + 1}. {c.title.trim() || 'Без названия'}</span><span>{c.kind === 'flag' ? 'Без баллов' : scorePoints(c.weight)}{issues.some(issue => issue.criterionIndex === i) && <small>Есть ошибки</small>}</span></summary>
      <fieldset aria-label={`Критерий ${i + 1}`}><legend>Настройки критерия {i + 1}</legend>
      <label className={editorStyles.name}>Название критерия<input {...fieldProps(`criterion-${i}-title`)} aria-label={`Критерий ${i + 1}: название критерия`} required value={c.title} onChange={e => change(i, {title: e.target.value})} placeholder="Например, Выяснение запроса клиента"/></label>
      <label>По каким признакам оценивать выполнение?<textarea {...fieldProps(`criterion-${i}-instruction`)} aria-label={`Критерий ${i + 1}: по каким признакам оценивать выполнение`} required rows={3} value={c.instruction} onChange={e => change(i, {instruction: e.target.value})} placeholder="Опишите, что считается полным, частичным выполнением или невыполнением."/></label>
      <div className={editorStyles.twoColumns}>
        <label>Способ оценки<select aria-label="Способ оценки" value={c.kind} onChange={e => change(i, {kind: e.target.value as Criterion['kind'], weight: e.target.value === 'flag' ? 0 : c.weight})}><option value="binary">Да или нет</option><option value="scale">Несколько уровней</option><option value="flag">Только отметка, без баллов</option></select></label>
        <label>Максимум баллов<input {...fieldProps(`criterion-${i}-weight`)} aria-label="Максимум баллов" type="number" min="0" step="any" required disabled={c.kind === 'flag'} value={c.weight} onChange={e => change(i, {weight: Number(e.target.value)})}/><small>{c.kind === 'flag' ? 'Отметки не влияют на итоговую оценку.' : 'За полное выполнение критерия. При изменении максимума баллы ответов пересчитываются пропорционально.'}</small></label>
      </div>
      <p className={editorStyles.weightExplanation}>{c.kind === 'flag' ? 'Этот критерий не участвует в расчёте оценки.' : <>В результате будут показаны полученные баллы и максимум — <b>{scorePoints(c.weight)}</b>. Ниже задайте баллы для каждого варианта ответа.</>}</p><div className={editorStyles.answersHeading}><h4>Варианты ответа</h4><p>{c.kind === 'flag' ? 'Опишите значение каждой отметки. Такие результаты показываются отдельно и не меняют оценку.' : 'Полное выполнение — максимум баллов. Частичное — меньше. Невыполнение — 0 баллов.'}</p></div>
      {c.levels.map((l, n) => <div key={n} className={editorStyles.answer}>
        <label>Название ответа<input {...fieldProps(`criterion-${i}-answer-${n}-value`)} aria-label={`Критерий ${i + 1}: название ответа ${n + 1}`} required value={answerLabel(l.value)} onChange={e => change(i, {levels: c.levels.map((x, k) => k === n ? {...x, value: e.target.value} : x)})}/></label>
        <label>Баллы за ответ<input {...fieldProps(`criterion-${i}-answer-${n}-fraction`)} aria-label={`Критерий ${i + 1}: баллы за ответ ${n + 1}`} type="number" step="any" min="0" max={c.weight} required disabled={c.kind === 'flag' || c.weight === 0} value={c.weight * l.fraction} onChange={e => c.weight > 0 && change(i, {levels: c.levels.map((x, k) => k === n ? {...x, fraction: Number(e.target.value) / c.weight} : x)})}/><small>{c.kind === 'flag' ? 'Без баллов' : `Максимум: ${scoreNumber(c.weight)}`}</small></label>
        <label className={editorStyles.answerDescription}>Когда выбирать этот ответ?<input {...fieldProps(`criterion-${i}-answer-${n}-description`)} aria-label={`Критерий ${i + 1}: условие ответа ${n + 1}`} required value={l.description} onChange={e => change(i, {levels: c.levels.map((x, k) => k === n ? {...x, description: e.target.value} : x)})}/></label>
        <button className={editorStyles.remove} type="button" aria-label={`Удалить ответ ${n + 1} из критерия ${i + 1}`} onClick={() => change(i, {levels: c.levels.filter((_, k) => k !== n)})}>Удалить</button>
      </div>)}
      <button {...fieldProps(`criterion-${i}-levels`)} type="button" onClick={() => change(i, {levels: [...c.levels, {value: nextAnswerValue(c.levels), fraction: 0.5, description: ''}]})}>Добавить вариант</button>
      <details className={editorStyles.technical}><summary>Исключения и правила для звонков</summary>
        <label>Когда критерий не применяется?<input aria-label="Условие неприменимости" value={c.na_condition || ''} onChange={e => change(i, {na_condition: e.target.value || null})} placeholder="Оставьте пустым, если критерий применяется всегда."/></label>
        <label>Дополнительные правила для звонков<textarea aria-label="Правила для звонков" rows={2} value={c.channel_guidance['voice call'] || ''} onChange={e => change(i, {channel_guidance: {...c.channel_guidance, 'voice call': e.target.value}})}/></label>
      </details>
      <details className={editorStyles.technical}><summary>Технические сведения</summary><label>ID критерия<input {...fieldProps(`criterion-${i}-id`)} aria-label="ID" required value={c.id} onChange={e => change(i, {id: e.target.value})}/></label></details>
      <div className={editorStyles.itemFooter}><button className={editorStyles.remove} type="button" onClick={() => removeItem(i)}>Удалить критерий</button></div>
      </fieldset>
    </details>)}
    <button type="button" onClick={addItem}>Добавить критерий</button>
    <p className={editorStyles.help}>Изменения сохраняются в новой версии. Прежние результаты остаются связаны с исходным чек-листом.</p>
  </form>
}
