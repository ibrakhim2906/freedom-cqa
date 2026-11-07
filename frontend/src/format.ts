export const terminal = new Set(['completed', 'failed', 'interrupted', 'cancelled'])
export const dollars = (n: number) => `$${n.toFixed(4)}`
const formatter = new Intl.DateTimeFormat('en-GB', {timeZone: 'Asia/Qyzylorda', dateStyle: 'medium', timeStyle: 'short'})
export const date = (s: string) => formatter.format(new Date(s))
export const safeLink = (url?: string) => url && /^https?:\/\//i.test(url) ? url : undefined
