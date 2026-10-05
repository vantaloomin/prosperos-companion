import type { DeletePreview, Layer, Memory, PlanStatus } from '../../types'

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
export function suggestionReason(reason: string | null, replaces: string[] = []): string {
  if (reason === 'sensitive') return 'Sensitive details are only kept when you say so.'
  if (reason === 'conflict') {
    const earlier = replaces.length ? ` from “${replaces.join('”, “')}”` : ''
    return `This is different${earlier}, and you didn't say it changed. Remember replaces the earlier value, which is kept as history.`
  }
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

const OPEN_PLANS: (string | null)[] = ['proposed', 'agreed', 'postponed']

/** A plan still open after its date: the date passing does not say whether it happened (PRD M6). */
function pastOpenPlan(memory: Memory, now: Date): boolean {
  return OPEN_PLANS.includes(memory.plan_status) && !!memory.applies_from && new Date(memory.applies_from) < now
}

/** The one focused question worth asking about a memory, if any (PRD M8). */
export function followUp(memory: Memory, now: Date): 'outcome' | 'date' | null {
  if (memory.status !== 'active') return null
  if (pastOpenPlan(memory, now)) return 'outcome'
  return memory.dates_uncertain ? 'date' : null
}

/** A timestamp as the local day a date input shows. */
export function dayInput(value: string | null): string {
  if (!value) return ''
  const day = new Date(value)
  return [day.getFullYear(), String(day.getMonth() + 1).padStart(2, '0'), String(day.getDate()).padStart(2, '0')].join('-')
}

/** A date input's day as local midnight, the way the server stores spans. */
function dayStamp(day: string): string | undefined {
  return day ? new Date(`${day}T00:00`).toISOString() : undefined
}

export interface CorrectionDraft { value: string; plan_status: PlanStatus | null; from: string; until: string }

export interface Correction { value: string; plan_status?: PlanStatus; applies_from?: string; applies_until?: string }

/** A day to send: changed, or unchanged but uncertain, so saving it confirms it. */
function sentDay(day: string, current: string | null, uncertain: boolean): string | undefined {
  return day && (uncertain || day !== dayInput(current)) ? dayStamp(day) : undefined
}

/** Only what changed is sent; null when nothing did. */
export function correction(memory: Memory, draft: CorrectionDraft): Correction | null {
  const uncertain = !!memory.dates_uncertain
  const body: Correction = {
    value: draft.value.trim(),
    plan_status: draft.plan_status !== memory.plan_status ? draft.plan_status ?? undefined : undefined,
    applies_from: sentDay(draft.from, memory.applies_from, uncertain),
    applies_until: sentDay(draft.until, memory.applies_until, uncertain),
  }
  const extras = [body.plan_status, body.applies_from, body.applies_until].some((item) => item !== undefined)
  return body.value && (extras || body.value !== memory.value) ? body : null
}
