import type { Turn } from './turns.ts'

/** A line of the app's in the chat, placed by when it happened: a look change, or a Story visit (storyVisits.ts). */
type Note = { at: string }

/** When a turn's last message was written. */
function ended(turn: Turn) {
  return [...turn.leads, turn.user, ...turn.attempts].reduce((last, message) => message && message.created_at > last ? message.created_at : last, '')
}

/** The look changes that go just before a turn: after the turn before it ended, up to this one's end, so each line shows
 * once. Changes before the first turn shown wait for earlier messages to load, so a line never sits above history it
 * came after. */
export function notesBefore<T extends Note>(notes: T[], turns: Turn[], index: number): T[] {
  if (index === 0) return []
  const after = ended(turns[index - 1]), until = ended(turns[index])
  return notes.filter((note) => note.at > after && note.at <= until)
}

/** The changes since the newest turn, after it. */
export function notesAfter<T extends Note>(notes: T[], turns: Turn[]): T[] {
  const last = turns.at(-1)
  return last ? notes.filter((note) => note.at > ended(last)) : notes
}
