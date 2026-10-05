import type { Message } from '../../types'

export interface Turn {
  user: Message
  /** Every reply attempt to this message, oldest first. */
  attempts: Message[]
}

/** Pair each user message with its reply attempts. Attempts whose message is on an unloaded page are left out. */
export function groupTurns(messages: Message[]): Turn[] {
  const turns: Turn[] = []
  const byId = new Map<string, Turn>()
  for (const message of [...messages].sort((a, b) => a.seq - b.seq)) {
    if (message.role === 'user') {
      const turn = { user: message, attempts: [] }
      turns.push(turn)
      byId.set(message.id, turn)
    } else if (message.reply_to) {
      byId.get(message.reply_to)?.attempts.push(message)
    }
  }
  return turns
}

/**
 * The attempt shown by default. On the latest message it is the newest attempt, so a reply being
 * written, or one that just failed, is never hidden behind an earlier one. Older messages show
 * their active reply, falling back to the newest attempt.
 */
export function defaultAttempt(turn: Turn, latest = false): Message | null {
  const active = turn.attempts.find((attempt) => attempt.active && attempt.status === 'complete')
  return (latest ? undefined : active) ?? turn.attempts.at(-1) ?? null
}

export function streamingIds(messages: Message[]): string[] {
  return messages.filter((message) => message.role === 'companion' && message.status === 'streaming').map((message) => message.id)
}

/** Add or replace messages by id, keeping sequence order. */
export function mergeMessages(current: Message[], incoming: (Message | null | undefined)[]): Message[] {
  const byId = new Map(current.map((message) => [message.id, message]))
  for (const message of incoming) if (message) byId.set(message.id, message)
  return [...byId.values()].sort((a, b) => a.seq - b.seq)
}

/** A reply that finished as active replaces any earlier active reply to the same message. */
export function applyFinished(current: Message[], reply: Message): Message[] {
  const settled = reply.active ? current.map((message) => message.reply_to === reply.reply_to && message.id !== reply.id ? { ...message, active: false } : message) : current
  return mergeMessages(settled, [reply])
}

const STATUS_NOTES: Record<string, string> = {
  incomplete: 'This reply is incomplete.',
  cancelled: 'You stopped this reply.',
  failed: 'This reply failed.',
  withheld: 'This reply was set aside because memories or the character changed while it was written.',
}

export function statusNote(message: Message): string | null {
  return STATUS_NOTES[message.status] ?? null
}

/** The note shown under an unfinished reply, with its error unless that only repeats that it was stopped. */
export function statusDetail(message: Message): string | null {
  const note = statusNote(message)
  return note && `${note}${message.error && message.error !== 'Stopped.' ? ` ${message.error}` : ''}`
}

/** What screen readers hear when a reply finishes: the same words the reply shows. */
export function replyAnnouncement(name: string, reply: Message): string {
  return reply.status === 'complete' ? `${name} replied.` : statusDetail(reply) ?? `The reply ended: ${reply.status}.`
}

/** The attempt to show: the one the reader paged to, else one search pointed at, else the default. */
export function shownAttempt(turn: Turn, isLatest: boolean, chosen: string | null, highlight?: string | null): Message | null {
  const pick = (id?: string | null) => (id ? turn.attempts.find((attempt) => attempt.id === id) : undefined)
  return pick(chosen) ?? pick(highlight) ?? defaultAttempt(turn, isLatest)
}
