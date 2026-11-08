import type {Checklist, JobDetail} from './types'
import {criterionOutcome, hasBooleanFlagScale, scoreNumber} from './scorePresentation'
import styles from './GradeOverview.module.css'

export function GradeOverview({effective, checklist, provisional, reviewCriteria, originalTotal}: {
  effective: NonNullable<JobDetail['effective']>; checklist: Checklist; provisional: boolean;
  reviewCriteria: Set<string>; originalTotal?: number|null;
}) {
  const total = effective.score.total
  const qualified = provisional || reviewCriteria.size > 0
  const heading = total === null ? 'Оценка ещё не выставлена' : provisional ? 'Предварительная оценка'
    : reviewCriteria.size > 0 ? 'Оценка требует проверки' : 'Итоговая оценка'

  function inspect(id: string) {
    const target = document.getElementById(`criterion-${id}`)
    target?.querySelectorAll('details[data-criterion-details], details[data-review-notes]').forEach(details => {
      if (details instanceof HTMLDetailsElement) details.open = true
    })
    target?.scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start'})
    target?.focus({preventScroll: true})
  }

  return <section className={styles.overview} data-testid="score" aria-label="Общая оценка и баллы по критериям">
    <div className={styles.layout}>
      <div className={styles.summary} data-qualified={qualified} data-empty={total === null}>
        <h3>{heading}</h3>
        <div className={styles.ring} role={total === null ? 'img' : 'meter'} aria-label={heading}
          aria-valuemin={total === null ? undefined : 0} aria-valuemax={total === null ? undefined : 100}
          aria-valuenow={total === null ? undefined : total}
          aria-valuetext={total === null ? undefined : `${scoreNumber(total)} из 100`}>
          <svg viewBox="0 0 160 160" aria-hidden="true" focusable="false">
            <circle className={styles.track} cx="80" cy="80" r="68"/>
            {total !== null && total > 0 && <circle className={styles.progress} cx="80" cy="80" r="68"
              pathLength="100" strokeDasharray={`${Math.min(100, Math.max(0, total))} 100`} transform="rotate(-90 80 80)"/>}
          </svg>
          <div className={styles.number} aria-hidden="true"><strong>{total === null ? '—' : scoreNumber(total)}</strong><span>{total === null ? 'Пока без оценки' : 'из 100'}</span></div>
        </div>
        <p className={styles.checklistName}>Чек-лист: {checklist.title}</p>
        <span className={styles.origin}>{effective.source === 'human_review'
          ? `После пересмотра · исходная оценка: ${originalTotal == null ? 'не выставлена' : `${scoreNumber(originalTotal)} из 100`}`
          : effective.source === 'prepared_demo' ? 'Заранее подготовленный пример' : 'Автоматическая проверка'}</span>
      </div>
      <div className={styles.breakdown}>
        <div className={styles.columns}><span>Критерий</span><span>Получено / максимум</span></div>
        <ol className={styles.rows}>
          {checklist.criteria.map((criterion, index) => {
            const judgment = effective.judgments.find(item => item.criterion_id === criterion.id)
            const contribution = effective.score.contributions.find(item => item.criterion_id === criterion.id)
            const flag = criterion.kind === 'flag'
            const zeroWeight = !flag && criterion.weight === 0
            const notApplicable = judgment?.status === 'not_applicable'
            const pending = judgment?.status === 'needs_review'
            const review = reviewCriteria.has(criterion.id) || pending || !!judgment?.uncertainty?.trim()
            const recordedPoints = judgment?.status === 'scored' && !flag ? contribution?.points : null
            const pointsMissing = judgment?.status === 'scored' && !flag && !zeroWeight && recordedPoints == null
            const maximumAllowed = criterion.weight * Math.max(...criterion.levels.map(level => level.fraction))
            const deducted = recordedPoints != null && maximumAllowed - recordedPoints > 1e-8 * Math.max(1, maximumAllowed)
            const activeFlag = flag && hasBooleanFlagScale(criterion) && judgment?.status === 'scored' && judgment.answer === 'yes'
            const outcome = judgment ? criterionOutcome(criterion, judgment) : 'Результат не сохранён'
            const value = !judgment ? '—' : notApplicable ? 'Не применяется' : pending ? 'Нужно решение'
              : flag ? outcome : zeroWeight ? 'Без баллов' : recordedPoints == null ? '—' : `${scoreNumber(recordedPoints)} / ${scoreNumber(criterion.weight)}`
            const valueDescription = !judgment ? 'Результат не сохранён' : notApplicable ? 'Не применяется'
              : pending ? 'Нужно решение' : flag ? `Отдельная отметка: ${outcome}. На оценку не влияет`
                : zeroWeight ? 'Критерий без баллов. На итоговую оценку не влияет'
                : recordedPoints == null ? 'Данные о баллах не сохранены'
                  : `Получено ${scoreNumber(recordedPoints)} из ${scoreNumber(criterion.weight)} баллов`
            const note = flag ? `Отдельная отметка · ${review ? 'требует внимания' : 'без баллов'}`
              : pointsMissing ? `Данные о баллах не сохранены${review ? ' · требует внимания' : ''}`
              : review ? 'Требует внимания' : deducted ? 'Баллы снижены' : notApplicable ? 'Исключён из расчёта'
                : criterion.weight === 0 ? 'На оценку не влияет' : ''
            return <li key={criterion.id}>
              <button type="button" className={styles.row} disabled={!judgment} onClick={() => inspect(criterion.id)}
                data-attention={review || activeFlag} data-deducted={deducted} data-excluded={notApplicable}
                aria-label={`${index + 1}. ${criterion.title}. ${valueDescription}.${review ? ' Требует внимания.' : ''} Открыть обоснование.`}>
                <span className={styles.index} aria-hidden="true">{index + 1}</span>
                <span className={styles.title}><span>{criterion.title}</span>{note && <small>{note}</small>}</span>
                <span className={`${styles.value} ${recordedPoints == null || flag || zeroWeight ? styles.textValue : ''}`}>{value}</span>
              </button>
            </li>
          })}
        </ol>
        <p className={styles.hint}>Нажмите на критерий, чтобы открыть обоснование и цитаты.</p>
      </div>
    </div>
  </section>
}
