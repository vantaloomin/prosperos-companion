import type { DeletePreview, Layer, Memory } from '../../types'

export const LAYERS: { id: Layer; title: (name: string) => string; hint: string }[] = [
  { id: 'user_fact', title: () => 'About you', hint: 'Facts, preferences and boundaries. They last until you correct them.' },
  { id: 'plan', title: () => 'Plans and commitments', hint: 'A plan stays open until it is marked done or cancelled; a date passing does not finish it.' },
  { id: 'temporary', title: () => 'Right now', hint: 'Passing circumstances, used only while they apply.' },
  { id: 'shared_experience', title: () => 'Shared moments', hint: 'Conversations and moments recalled when they become relevant.' },
  { id: 'relationship', title: () => 'Your relationship', hint: 'Agreements, boundaries and how things were resolved.' },
  { id: 'companion_life', title: (name) => `${name}'s life`, hint: 'Fictional events in their life. They never describe what you did.' },
]

export function layerTitle(layer: Layer, name: string) {
  return LAYERS.find((item) => item.id === layer)?.title(name) ?? layer
}

export interface MemoryGroup { layer: Layer; current: Memory[]; history: Memory[] }

/** Group by layer in display order; pinned first, then by subject. Superseded versions stay as history. */
export function groupMemories(memories: Memory[]): MemoryGroup[] {
  return LAYERS.map(({ id }) => {
    const inLayer = memories.filter((memory) => memory.layer === id)
    const order = (a: Memory, b: Memory) => Number(b.pinned) - Number(a.pinned) || Number(b.boundary) - Number(a.boundary) || a.subject.localeCompare(b.subject)
    return {
      layer: id,
      current: inLayer.filter((memory) => memory.status !== 'superseded').sort(order),
      history: inLayer.filter((memory) => memory.status === 'superseded'),
    }
  }).filter((group) => group.current.length || group.history.length)
}

/** Earlier values of one memory, newest first, following its supersession links. */
export function earlierVersions(memory: Memory, all: Memory[]): Memory[] {
  const byId = new Map(all.map((item) => [item.id, item]))
  const result: Memory[] = []
  let next = memory.supersedes_id ? byId.get(memory.supersedes_id) : undefined
  while (next && !result.includes(next)) {
    result.push(next)
    next = next.supersedes_id ? byId.get(next.supersedes_id) : undefined
  }
  return result
}

const FLAG_LABELS: [(memory: Memory) => boolean | undefined, string][] = [
  [(memory) => memory.boundary, 'Boundary'],
  [(memory) => memory.pinned, 'Pinned'],
  [(memory) => memory.status === 'excluded', 'Not used in conversation'],
  [(memory) => memory.authority === 'tentative', 'Unconfirmed guess'],
  [(memory) => memory.authority === 'confirmed', 'Confirmed by you'],
  [(memory) => memory.sensitive, 'Sensitive'],
]

/** Plain-language state, never a confidence score. */
export function statusLabels(memory: Memory): string[] {
  const labels = FLAG_LABELS.filter(([applies]) => applies(memory)).map(([, label]) => label)
  if (memory.plan_status) labels.push(memory.plan_status[0].toUpperCase() + memory.plan_status.slice(1))
  if (memory.current === false && memory.status !== 'superseded' && !memory.plan_status) labels.push('No longer current')
  if (memory.dates_uncertain) labels.push('Dates uncertain')
  if (memory.origin === 'automatic') labels.push('Saved automatically')
  return labels
}

/** Why a suggestion is waiting, in words. */
export function suggestionReason(reason: string | null): string {
  if (reason === 'sensitive') return 'Sensitive details are only kept when you say so.'
  if (reason === 'model_guess') return 'Suggested by the model from your words. It is only kept if you say so.'
  return 'Waiting for you to decide.'
}

/** What Remember this did, for the notice under the conversation. */
export function rememberedText(name: string, memories: { subject: string; value: string }[]): string {
  const items = memories.map((memory) => `${memory.subject}: ${memory.value}`)
  return `${name} will remember ${items.length === 1 ? 'this' : 'these'}: ${items.join('; ')}.`
}

export const REMEMBER_KEY = 'companion:remember'

export interface RememberRequest { messageId: string; text: string }

/** Plain lines for the delete dialog: what goes with the messages, and what stays. */
export function deletePreviewText(preview: DeletePreview, withSources: boolean): string[] {
  if (!withSources) return []
  const lines: string[] = []
  const count = preview.source_message_ids.length
  if (count) lines.push(`${count} message${count === 1 ? '' : 's'} will show as deleted in your conversation.`)
  if (preview.summaries_with_sources) lines.push(`${preview.summaries_with_sources} conversation summar${preview.summaries_with_sources === 1 ? 'y' : 'ies'} quoting them will be removed.`)
  if (preview.other_memories.length) lines.push(`Also from those messages, and kept: ${preview.other_memories.map((item) => item.subject).join(', ')}.`)
  return lines
}
