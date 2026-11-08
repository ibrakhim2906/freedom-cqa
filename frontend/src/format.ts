export const terminal = new Set(['completed', 'failed', 'interrupted', 'cancelled'])
const currency = new Intl.NumberFormat('ru-RU', {style: 'currency', currency: 'USD', minimumFractionDigits: 4, maximumFractionDigits: 4})
export const dollars = (n: number) => currency.format(n)
const formatter = new Intl.DateTimeFormat('ru-RU', {timeZone: 'Asia/Qyzylorda', dateStyle: 'medium', timeStyle: 'short'})
export const date = (s: string) => formatter.format(new Date(s))
export const safeLink = (url?: string|null) => url && /^https?:\/\//i.test(url) ? url : undefined
export const referenceDate = (ref: {date_basis?: string; snapshot_on?: string|null; valid_from?: string|null; valid_until?: string|null}) =>
  ref.date_basis === 'snapshot' ? `Сведения на ${ref.snapshot_on || 'неуказанную дату'} (не дата вступления правил в силу)` :
    `Период действия: ${ref.valid_from || 'начало не указано'} — ${ref.valid_until || 'окончание не указано'}`

export const referenceReason = (reason: string) => ({
  reference_context_scope_mismatch: 'контекст проверки не соответствует продукту',
  reference_context_scope_unconfirmed: 'принадлежность к продукту не подтверждена',
  missing_scope: 'продукт не указан', scope_mismatch: 'документ относится к другому продукту',
  source_date_conflict: 'даты в исходных данных противоречат друг другу',
  missing_assessment_date: 'не указана дата проверки', missing_occurrence_date: 'неизвестна дата диалога',
  snapshot_date_mismatch: 'дата сохранённого документа не совпадает с датой проверки',
  before_validity_window: 'диалог состоялся до начала действия документа',
  after_validity_window: 'диалог состоялся после окончания действия документа',
  timestamps_span_multiple_source_dates: 'сообщения относятся к разным датам',
  explicit_date_conflicts_with_source_timestamps: 'указанная дата не совпадает с датами сообщений',
  derived_date_provenance_not_supported_by_source: 'дату нельзя подтвердить по исходным сообщениям',
  no_nonempty_timestamps: 'в сообщениях нет отметок времени',
  timestamps_not_all_offset_aware_iso8601: 'не во всех сообщениях указаны полная дата и часовой пояс',
} as Record<string, string>)[reason] || reason

export const dateOrigin = (origin: string) => ({explicit: 'указана при загрузке',
  iso_timestamp_consensus: 'определена по датам сообщений', conflict: 'в исходных датах есть противоречие',
  unavailable: 'не удалось определить', supplied: 'указана при загрузке', source_iso_timestamps: 'даты сообщений',
  unknown: 'неизвестен'} as Record<string, string>)[origin] || origin
