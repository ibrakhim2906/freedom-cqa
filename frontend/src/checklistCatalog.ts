import type {ChecklistRow} from './types'

// These IDs belong to shipped validation fixtures, not to user-created checklists.
// Keep their saved records intact so historical reviews retain their original rules.
const validationChecklistIds = new Set([
  'delivery-unseen-handoff',
  'delivery-followup-contract',
  'fresh-keyboard-review',
  'workflow-checklist-1794051744741',
])

function isValidationChecklist(checklist: ChecklistRow) {
  return validationChecklistIds.has(checklist.external_id)
}

export function visibleChecklists(checklists: ChecklistRow[], mainId: string, mainVersion?: string) {
  const latest = new Map<string, ChecklistRow>()
  // The API returns newest first. Dates also keep this correct for unordered data.
  const ordered = [...checklists].sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))
  for (const checklist of ordered) {
    if (isValidationChecklist(checklist) || latest.has(checklist.external_id)) continue
    latest.set(checklist.external_id, checklist)
  }
  const main = checklists.find(checklist => checklist.external_id === mainId && checklist.version === mainVersion)
  if (main) latest.set(mainId, main)
  return [...latest.values()].sort((a, b) => {
    const mainFirst = Number(b.external_id === mainId) - Number(a.external_id === mainId)
    if (mainFirst) return mainFirst
    return a.title.localeCompare(b.title)
  })
}

export function currentChecklistId(checklists: ChecklistRow[], mainId: string, selectedId: string, mainVersion?: string) {
  const visible = visibleChecklists(checklists, mainId, mainVersion)
  const selected = checklists.find(checklist => checklist.id === selectedId)
  return visible.find(checklist => checklist.external_id === selected?.external_id)?.id
    || visible[0]?.id || ''
}
