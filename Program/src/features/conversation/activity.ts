import type { Message } from '../../types'
import { isHeld, waitsUntilLater } from './held.ts'

/** What the app is doing for a reply before its text arrives (companion/conversation.py PHASES). */
export type Phase = 'preparing' | 'looking' | 'waiting' | 'writing'

/**
 * The line under the conversation saying what the app is doing. It describes the app's work, never
 * whether the companion is online, and never when a held reply will show.
 */
export function activityLine(messages: Message[], phases: Record<string, Phase>, sending: boolean, name: string, now: number): string {
  if (sending) return 'Sending…'
  const companion = messages.filter((message) => message.role === 'companion' && !message.superseded_at)
  const writing = companion.find((message) => message.status === 'streaming' && !isHeld(message, now))
  if (writing) return phaseLine(phases[writing.id])
  if (companion.some((message) => waitsUntilLater(message, now))) return `${name} will get back to you later.`
  return ''
}

function phaseLine(phase: Phase | undefined): string {
  if (phase === 'looking') return 'Looking at your picture…'
  if (phase === 'waiting') return 'Waiting for the model to be free…'
  if (phase === 'writing') return 'Writing a reply…'
  return 'Getting a reply ready…'
}

/** When the line next changes on its own: the earliest held reply's time, in milliseconds, else null. */
export function nextChange(messages: Message[], now: number): number | null {
  const times = messages.filter((message) => waitsUntilLater(message, now)).map((message) => Date.parse(message.held_until!))
  return times.length ? Math.min(...times) : null
}
