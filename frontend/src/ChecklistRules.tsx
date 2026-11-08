import type {Checklist} from './types'
import {ScoringHelp} from './ScoringHelp'
import {criterionOutcome, scoreNumber, scorePoints} from './scorePresentation'
import styles from './ChecklistRules.module.css'

export function ChecklistRules({checklist}: {checklist: Checklist}) {
  const total = checklist.criteria.filter(c => c.kind !== 'flag').reduce((sum, c) => sum + c.weight, 0)
  return <section className={styles.rules} aria-label="Правила начисления баллов">
    <div className={styles.intro}>
      <p>Здесь указан <b>максимум баллов</b> за каждый критерий. После проверки вы увидите, сколько получено: например, <b>10 / 15</b> — 10 из 15 возможных баллов.</p>
      <div className={styles.totals}><span>Всего в чек-листе: <b>{scorePoints(total)}</b></span><span>Итоговая оценка: <b>от 0 до 100</b></span></div>
    </div>
    {!!checklist.instructions.length && <details className={styles.general}><summary>Общие правила проверки</summary><ul>{checklist.instructions.map((rule, index) => <li key={index}>{rule}</li>)}</ul></details>}
    <div className={styles.list}>
      <div className={styles.heading}><span>Критерий</span><span>Максимум<small>за полное выполнение</small></span></div>
      {checklist.criteria.map((c, index) => <details className={styles.criterion} key={c.id}>
        <summary aria-label={`Критерий ${index + 1}: ${c.title} — ${c.kind === 'flag' || c.weight === 0 ? 'без баллов' : `максимум: ${scorePoints(c.weight)}`}`}>
          <span className={styles.number}>{index + 1}</span><span className={styles.title}>{c.title}</span>
          <span className={c.kind === 'flag' || c.weight === 0 ? styles.noPoints : styles.maximum}>{c.kind === 'flag' || c.weight === 0 ? 'Без баллов' : scorePoints(c.weight)}</span><span className={styles.chevron} aria-hidden="true">›</span>
        </summary>
        <div className={styles.detail}>
          <p>{c.instruction}</p>
          {c.kind === 'flag' && <p className={styles.hint}>Эта отметка отображается отдельно и не меняет итоговую оценку.</p>}
          <table><thead><tr><th>Вариант ответа</th><th>Баллы</th><th>Когда выбирать</th></tr></thead><tbody>
            {c.levels.map(l => <tr key={l.value}><td>{criterionOutcome(c, {status: 'scored', answer: l.value})}</td><td className={styles.answerPoints}>{c.kind === 'flag' ? 'Без баллов' : `${scoreNumber(c.weight * l.fraction)} / ${scoreNumber(c.weight)}`}</td><td>{l.description}</td></tr>)}
          </tbody></table>
          {c.na_condition && <p className={styles.hint}><b>Когда исключается из расчёта:</b> {c.na_condition}</p>}
          {Object.entries(c.channel_guidance).map(([channel, rule]) => <p className={styles.hint} key={channel}><b>{channel === 'voice call' ? 'Правила для звонков' : channel === 'agent chat' ? 'Правила для чатов' : `Правила для канала «${channel}»`}:</b> {rule}</p>)}
        </div>
      </details>)}
    </div>
    <p className={styles.hint}>Нажмите на критерий, чтобы посмотреть правило и варианты начисления баллов.</p>
    <ScoringHelp/>
  </section>
}
