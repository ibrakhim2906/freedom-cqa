export const terminal = new Set(['completed', 'failed', 'interrupted', 'cancelled'])
export const dollars = (n: number) => `$${n.toFixed(4)}`
const formatter = new Intl.DateTimeFormat('en-GB', {timeZone: 'Asia/Qyzylorda', dateStyle: 'medium', timeStyle: 'short'})
export const date = (s: string) => formatter.format(new Date(s))
export const safeLink = (url?: string|null) => url && /^https?:\/\//i.test(url) ? url : undefined
export const referenceDate = (ref: {date_basis?: string; snapshot_on?: string|null; valid_from?: string|null; valid_until?: string|null}) =>
  ref.date_basis === 'snapshot' ? `Source snapshot: ${ref.snapshot_on || 'unspecified'} (not a policy effective date)` :
    `Policy window: ${ref.valid_from || 'unspecified'}–${ref.valid_until || 'unspecified'}`
