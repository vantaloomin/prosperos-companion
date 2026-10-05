import type { Message } from '../../types'

/** Whether a reply is still held at `now` (milliseconds). */
export function isHeld(message: Pick<Message, 'held_until'>, now: number): boolean {
  return !!message.held_until && Date.parse(message.held_until) > now
}

/** The note under a held reply: when it shows, and why it waits. */
export function heldNote(message: Pick<Message, 'held_until' | 'held_line'>, name: string): string {
  const at = new Date(message.held_until!).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
  return message.held_line ? `${name} is busy. Their full reply shows at ${at}.` : `${name} is asleep. Their reply shows when they wake, at ${at}.`
}

/** Writing again shows any reply held before it, as the server does. */
export function releaseHeld(messages: Message[], seq: number): Message[] {
  return messages.map((message) => message.seq < seq && message.held_until ? { ...message, held_until: null } : message)
}
