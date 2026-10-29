import type { Message } from '../../types'

/** Whether a reply is still held at `now` (milliseconds): the companion has not got back to the user yet. */
export function isHeld(message: Pick<Message, 'held_until'>, now: number): boolean {
  return !!message.held_until && Date.parse(message.held_until) > now
}

/** A reply that shows at once shows every reply held before it, as the server does: from `at`, the new reply's time. */
export function releaseHeld(messages: Message[], seq: number, at: string): Message[] {
  return messages.map((message) => message.seq < seq && message.held_until && message.held_until > at ? { ...message, held_until: at } : message)
}

/** When the user got the message: a held reply when its time came (or when it was done, if the companion read it
 * later and wrote it after), not when the user's text arrived. A failed one shows when it failed. */
export function shownAt(message: Pick<Message, 'created_at' | 'completed_at' | 'held_until' | 'status'>): string {
  if (!message.held_until) return message.created_at
  if (message.status === 'failed' || message.status === 'incomplete') return message.completed_at ?? message.created_at
  return message.completed_at && message.completed_at > message.held_until ? message.completed_at : message.held_until
}

/** Out of sight until its time: a held reply being written or ready. One that failed shows at once, so an error is never hidden. */
export function waitsUntilLater(message: Pick<Message, 'held_until' | 'status'>, now: number): boolean {
  return isHeld(message, now) && (message.status === 'streaming' || message.status === 'complete')
}

/** The reply that shows last among those held until a time: the one to wait for before offering another reply. An
 * earlier version held once and long since shown never stands in for a newer one still waiting. */
export function lastHeld<T extends Pick<Message, 'held_until' | 'status'>>(messages: T[]): T | undefined {
  return messages.filter((message) => message.held_until && (message.status === 'streaming' || message.status === 'complete'))
    .reduce<T | undefined>((last, message) => (!last || message.held_until! > last.held_until! ? message : last), undefined)
}
