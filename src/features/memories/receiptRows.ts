import type { ContextReceipt, Memory } from '../../types'

/** Packet sections in the order the context builder fills them, worded for the person reading. */
const SECTIONS: { key: string; label: (name: string) => string; unit?: [string, string] }[] = [
  { key: 'character', label: (name) => `${name}'s character` },
  { key: 'boundaries', label: () => 'Your boundaries', unit: ['boundary', 'boundaries'] },
  { key: 'time', label: () => 'The time for both of you' },
  { key: 'conversation', label: () => 'Recent messages', unit: ['message', 'messages'] },
  { key: 'relationship_mood', label: (name) => `${name}'s mood about time apart` },
  { key: 'closeness', label: () => 'How close you are, and running jokes' },
  { key: 'profile', label: () => 'What they know about you', unit: ['memory', 'memories'] },
  { key: 'commitments', label: () => 'Open plans and commitments', unit: ['plan', 'plans'] },
  { key: 'temporary', label: () => 'Your current circumstances', unit: ['memory', 'memories'] },
  { key: 'people', label: () => 'People in your life', unit: ['item', 'items'] },
  { key: 'circle', label: (name) => `People in ${name}'s life`, unit: ['person', 'people'] },
  { key: 'companion_life', label: (name) => `${name}'s recent life`, unit: ['event', 'events'] },
  { key: 'feed_reference', label: () => 'The post you are replying to' },
  { key: 'photo', label: (name) => `What ${name} is doing now, for the photo` },
  { key: 'outside', label: () => 'Real-world lookups', unit: ['lookup', 'lookups'] },
  { key: 'real_events', label: (name) => `Real events in ${name}'s city` },
  { key: 'recalled', label: () => 'Possibly relevant memories', unit: ['memory', 'memories'] },
]
export const PREVIEW_KEY = ['context-preview']
const NAMED = 4

export interface ReceiptRow { key: string; label: string; included: number; omitted: number; detail: string }

/** One row per section that used or left out anything, naming remembered items where they are memories. */
export function receiptRows(receipt: ContextReceipt, memories: Memory[], name: string): ReceiptRow[] {
  const subjects = new Map(memories.map((memory) => [memory.id, memory.subject]))
  const known = new Set(SECTIONS.map((section) => section.key))
  const extra = [...Object.keys(receipt.included), ...Object.keys(receipt.omitted)].filter((key) => !known.has(key))
  const sections = [...SECTIONS, ...[...new Set(extra)].map((key) => ({ key, label: () => key.replace(/_/g, ' ') }))]
  return sections.flatMap(({ key, label, unit }: { key: string; label: (name: string) => string; unit?: [string, string] }) => {
    const included = receipt.included[key] ?? []
    const omitted = receipt.omitted[key] ?? []
    if (!included.length && !omitted.length) return []
    const names = included.map((id) => subjects.get(id)).filter((subject): subject is string => !!subject)
    return [{ key, label: label(name), included: included.length, omitted: omitted.length, detail: detail(included.length, names, unit) }]
  })
}

function detail(count: number, names: string[], unit?: [string, string]): string {
  if (names.length) return names.length > NAMED ? `${names.slice(0, NAMED).join(', ')} and ${names.length - NAMED} more` : names.join(', ')
  if (count === 0) return 'None included'
  if (!unit) return 'Included'
  return `${count} ${count === 1 ? unit[0] : unit[1]}`
}

export function budgetShare(receipt: ContextReceipt): number {
  if (receipt.budget_tokens <= 0) return 100
  return Math.min(100, Math.round((receipt.estimated_tokens / receipt.budget_tokens) * 100))
}
