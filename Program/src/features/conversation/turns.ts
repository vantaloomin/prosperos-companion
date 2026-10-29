import type { Message } from '../../types'

export interface Turn {
  /** Null for messages the companion sent first that nobody has answered yet. */
  user: Message | null
  /** Messages the companion sent first, before this user message. */
  leads: Message[]
  /** Every reply attempt to this message, oldest first. */
  attempts: Message[]
  /** Later versions of a lead (Another reply on the full reply after a holding text), by the first version's id. */
  versions: Record<string, Message[]>
}

/** The id of the newest turn's user message, when the newest turn has one. */
export function latestUser(turns: Turn[]): string | undefined {
  // A message from an old chat brought in is history, never answered again.
  const user = turns.at(-1)?.user
  return user && !user.import_id ? user.id : undefined
}

/** A turn brought in from an old chat file (companion/imports/chats.py). */
export function isImported(turn: Turn): boolean {
  return !!(turn.user ?? turn.leads[0]).import_id
}

/** Where older history from an old chat ends: after an imported turn that the next turn is not part of. */
export function endsOlderHistory(turns: Turn[], index: number): boolean {
  const next = turns[index + 1]
  return isImported(turns[index]) && (!next || !isImported(next))
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
  let versions: Record<string, Message[]> = {}
  for (const message of [...messages].sort((a, b) => a.seq - b.seq)) {
    if (message.role === 'user') {
      const turn = { user: message, leads, attempts: [], versions }
      leads = []
      versions = {}
      turns.push(turn)
      byId.set(message.id, turn)
    } else if (message.reply_to) {
      byId.get(message.reply_to)?.attempts.push(message)
    } else if (message.version_of) {
      // Versions of an earlier lead come before the next message of the user's, which is only sent after them.
      if (leads.some((lead) => lead.id === message.version_of)) (versions[message.version_of] ??= []).push(message)
    } else {
      leads.push(message)
    }
  }
  if (leads.length) turns.push({ user: null, leads, attempts: [], versions })
  return turns.map(settled)
}

const built = new WeakMap<Message, Turn>()

/** The turn built last time when none of its messages changed, so a memoized turn skips re-rendering. */
function settled(turn: Turn): Turn {
  const anchor = turn.user ?? turn.leads[0]
  const previous = built.get(anchor)
  const same = (left: Message[], right: Message[]) => left.length === right.length && left.every((message, index) => message === right[index])
  const sameVersions = (left: Record<string, Message[]>, right: Record<string, Message[]>) =>
    Object.keys(left).length === Object.keys(right).length && Object.keys(right).every((id) => left[id] && same(left[id], right[id]))
  if (previous && same(previous.attempts, turn.attempts) && same(previous.leads, turn.leads) && sameVersions(previous.versions, turn.versions)) return previous
  built.set(anchor, turn)
  return turn
}

/**
 * The attempt shown by default: the active reply, the version the conversation goes on from (one the user paged
 * back to stays). On the latest message a newer attempt that is being written, or that just failed, shows instead,
 * so it is never hidden behind an earlier one. With no active reply, the newest attempt.
 */
export function defaultAttempt(turn: Turn, latest = false): Message | null {
  return defaultVersion(turn.attempts, latest)
}

export function defaultVersion(versions: Message[], latest = false): Message | null {
  const active = versions.find((attempt) => attempt.active && attempt.status === 'complete')
  const newest = versions.at(-1) ?? null
  return latest && newest?.status !== 'complete' ? newest : active ?? newest
}

/** The full reply sent after the holding text that answered the user's newest message, when it is in the chat. */
export function followUpAfter(turns: Turn[]): Message | undefined {
  const last = turns.at(-1)
  return last && !last.user ? [...last.leads].reverse().find((lead) => !!lead.held_line) : undefined
}

/** Every version of a lead, first one first: the lead alone unless Another reply was asked for on it. */
export function leadVersions(turn: Turn, lead: Message): Message[] {
  return [lead, ...(turn.versions[lead.id] ?? [])]
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

/** Which reply a version is a version of (companion/reply_versions.py): the message it answers, or for the full reply
 * after a holding text, its first version. Null for a message with no other versions. */
function versionGroup(message: Message): string | null {
  if (message.reply_to) return `reply:${message.reply_to}`
  const first = message.version_of ?? (message.held_line && message.role === 'companion' ? message.id : null)
  return first && `version:${first}`
}

/** A reply that finished as active replaces any earlier active version of it. */
export function applyFinished(current: Message[], reply: Message): Message[] {
  const group = versionGroup(reply)
  const settled = reply.active && group ? current.map((message) => message.id !== reply.id && versionGroup(message) === group ? { ...message, active: false } : message) : current
  return mergeMessages(settled, [reply])
}

/** Paged to an earlier version and left there: it becomes the active one, as the server records. */
export function applyChosen(current: Message[], chosen: Message): Message[] {
  return applyFinished(current, { ...chosen, active: true })
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
  const writing = [...turn.attempts, ...turn.leads, ...Object.values(turn.versions).flat()]
  return writing.some((message) => message.id in live) ? live : NO_LIVE
}
