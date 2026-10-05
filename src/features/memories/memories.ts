import type { Layer, Memory } from '../../types'

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

/** Plain-language state, never a confidence score. */
export function statusLabels(memory: Memory): string[] {
  const labels: string[] = []
  if (memory.boundary) labels.push('Boundary')
  if (memory.pinned) labels.push('Pinned')
  if (memory.status === 'excluded') labels.push('Not used in conversation')
  if (memory.authority === 'tentative') labels.push('Unconfirmed guess')
  if (memory.authority === 'confirmed') labels.push('Confirmed by you')
  if (memory.sensitive) labels.push('Sensitive')
  if (memory.plan_status) labels.push(memory.plan_status[0].toUpperCase() + memory.plan_status.slice(1))
  return labels
}

export const REMEMBER_KEY = 'companion:remember'

export interface RememberRequest { messageId: string; text: string }
