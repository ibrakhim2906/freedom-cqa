import type {ConversationRow} from './types'

export function groupConversationRevisions(conversations: ConversationRow[]) {
  const grouped = new Map<string, ConversationRow[]>()
  for (const conversation of conversations) {
    const revisions = grouped.get(conversation.external_id) || []
    revisions.push(conversation)
    grouped.set(conversation.external_id, revisions)
  }
  return [...grouped.entries()].map(([externalId, revisions]) => {
    revisions.sort((a, b) => b.created_at.localeCompare(a.created_at))
    return {externalId, latest: revisions[0], revisions}
  }).sort((a, b) => b.latest.created_at.localeCompare(a.latest.created_at))
}
