import {useState} from 'react'
import styles from './ScoringHelp.module.css'

const initialItems = [{weight: 20, credit: 100}, {weight: 10, credit: 50}]

export function ScoringHelp() {
  const [items, setItems] = useState(initialItems)
  const [secondExcluded, setSecondExcluded] = useState(false)
  const included = items.filter((_, index) => index === 0 || !secondExcluded)
  const weight = included.reduce((sum, item) => sum + item.weight, 0)
  const points = included.reduce((sum, item) => sum + item.weight * item.credit / 100, 0)
  const grade = weight > 0 ? Math.round(points * 10000 / weight) / 100 : null
  const change = (index: number, field: 'weight' | 'credit', value: number) => {
    setItems(items.map((item, i) => i === index ? {...item, [field]: value} : item))
  }

  const number = (value: number) => value.toLocaleString('ru-RU', {maximumFractionDigits: 2})
  return <details className={styles.help}>
    <summary>Как рассчитывается оценка</summary>
    <div className={styles.content}>
      <p>У каждого критерия есть баллы за полное выполнение. Ответ определяет, какую их долю получает диалог. Например, <b>50% от 20 баллов — это 10 баллов</b>.</p>
      <p className={styles.formula}>Итог = полученные баллы ÷ доступные баллы × 100</p>
      <ul>
        <li><b>Не применяется:</b> критерий исключается из расчёта вместе со своими баллами. Сумма баллов в чек-листе не обязана быть равна 100.</li>
        <li><b>Отметки без баллов:</b> показываются отдельно и не прибавляют и не вычитают баллы.</li>
        <li><b>Оценка ещё не выставлена:</b> если по одному из оцениваемых критериев нет решения, итог не рассчитывается. Отдельные отметки без баллов его не блокируют. Итог также не рассчитывается, если ни один применимый критерий не даёт баллов.</li>
        <li><b>Предварительная оценка:</b> часть выводов требует уточнения или зависит от предположений о справочных материалах. Причина указана рядом с результатом.</li>
      </ul>
      <div className={styles.example}>
        <div className={styles.exampleHeading}><b>Посчитайте на примере</b><button type="button" onClick={() => {setItems(initialItems); setSecondExcluded(false)}}>Сбросить пример</button></div>
        <p>Это учебный расчёт. Он не меняет чек-лист или сохранённые оценки.</p>
        <div className={styles.items}>
          {items.map((item, index) => <div key={index} className={styles.item} role="group" aria-label={`Критерий ${index + 1} в примере`}>
            <b>Критерий {index + 1}</b>
            <label><span>За полное выполнение: {number(item.weight)} баллов</span><input type="range" min="0" max="50" step="5" value={item.weight} aria-label={`Баллы за критерий ${index + 1}`} onChange={event => change(index, 'weight', Number(event.target.value))}/></label>
            <label><span>Начислить: {item.credit}% баллов</span><input type="range" min="0" max="100" step="5" value={item.credit} aria-label={`Доля баллов за критерий ${index + 1}`} onChange={event => change(index, 'credit', Number(event.target.value))}/></label>
            <span className={styles.points}>{index === 1 && secondExcluded ? 'Не участвует в расчёте' : `Получено ${number(item.weight * item.credit / 100)} из ${number(item.weight)} баллов`}</span>
          </div>)}
        </div>
        <label className={styles.notApplicable}><input type="checkbox" checked={secondExcluded} onChange={event => setSecondExcluded(event.target.checked)}/>Критерий 2 не применяется</label>
        <output className={styles.result} aria-live="polite" aria-atomic="true"><b>Итог в примере: {grade === null ? 'оценка не рассчитывается' : `${number(grade)} из 100`}</b><span>{grade === null ? 'Нет применимых критериев с баллами.' : `${number(points)} из ${number(weight)} баллов → ${number(grade!)} из 100`}</span></output>
      </div>
    </div>
  </details>
}
