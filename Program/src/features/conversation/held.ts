import type { Message } from '../../types'

/** Whether a reply is still held at `now` (milliseconds): the companion has not got back to the user yet. */
export function isHeld(message: Pick<Message, 'held_until'>, now: number): boolean {
  return !!message.held_until && Date.parse(message.held_until) > now
}

/** A reply that shows at once shows every reply held before it, as the server does. */
export function releaseHeld(messages: Message[], seq: number): Message[] {
  return messages.map((message) => message.seq < seq && message.held_until ? { ...message, held_until: null } : message)
}

/** Out of sight until its time: a held reply being written or ready. One that failed shows at once, so an error is never hidden. */
export function waitsUntilLater(message: Pick<Message, 'held_until' | 'status'>, now: number): boolean {
  return isHeld(message, now) && (message.status === 'streaming' || message.status === 'complete')
}
