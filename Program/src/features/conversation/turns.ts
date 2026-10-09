import type { Message } from '../../types'

export interface Turn {
  /** Null for messages the companion sent first that nobody has answered yet. */
  user: Message | null
  /** Messages the companion sent first, before this user message. */
  leads: Message[]
  /** Every reply attempt to this message, oldest first. */
  attempts: Message[]
}

/** The id of the newest turn's user message, when the newest turn has one. */
export function latestUser(turns: Turn[]): string | undefined {
  return turns.at(-1)?.user?.id
}

/** The id of the newest loaded message the user sent (messages are in sequence order). */
export function lastUserMessage(messages: Message[]): string | undefined {
  for (let index = messages.length - 1; index >= 0; index -= 1) if (messages[index].role === 'user') return messages[index].id
  return undefined
}

/** A stable key: the user message, or the first message the companion sent unprompted. */
export function turnKey(turn: Turn): string {
  return (turn.user ?? turn.leads[0]).id
}

/** Pair each user message with its reply attempts. Attempts whose message is on an unloaded page are left out. */
export function groupTurns(messages: Message[]): Turn[] {
  const turns: Turn[] = []
  const byId = new Map<string, Turn>()
  let leads: Message[] = []
  for (const message of [...messages].sort((a, b) => a.seq - b.seq)) {
    if (message.role === 'user') {
      const turn = { user: message, leads, attempts: [] }
      leads = []
      turns.push(turn)
      byId.set(message.id, turn)
    } else if (message.reply_to) {
      byId.get(message.reply_to)?.attempts.push(message)
    } else {
      leads.push(message)
    }
  }
  if (leads.length) turns.push({ user: null, leads, attempts: [] })
  return turns.map(settled)
}

const built = new WeakMap<Message, Turn>()

/** The turn built last time when none of its messages changed, so a memoized turn skips re-rendering. */
function settled(turn: Turn): Turn {
  const anchor = turn.user ?? turn.leads[0]
  const previous = built.get(anchor)
  const same = (left: Message[], right: Message[]) => left.length === right.length && left.every((message, index) => message === right[index])
  if (previous && same(previous.attempts, turn.attempts) && same(previous.leads, turn.leads)) return previous
  built.set(anchor, turn)
  return turn
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
/** A reply the user stopped, or one the model cut short: Edit finishes it by hand (companion/message_edits.py). */
export function unfinished(message: Message): boolean {
  return (message.status === 'cancelled' || message.status === 'incomplete') && !message.superseded_at
}

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

const NO_LIVE: Record<string, string> = {}

/**
 * The streamed text a turn needs: the live map for a turn with an attempt being written, else one
 * shared empty map, so a memoized turn that is not streaming keeps equal props and skips re-rendering.
 */
export function liveFor(turn: Turn, live: Record<string, string>): Record<string, string> {
  return turn.attempts.some((attempt) => attempt.id in live) ? live : NO_LIVE
}
