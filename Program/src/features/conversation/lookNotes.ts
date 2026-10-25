import type { Turn } from './turns.ts'

type Note = { text: string; at: string }

/** When a turn's last message was written. */
function ended(turn: Turn) {
  return [...turn.leads, turn.user, ...turn.attempts].reduce((last, message) => message && message.created_at > last ? message.created_at : last, '')
}

/** The look changes that go just before a turn: after the turn before it ended, up to this one's end, so each line shows
 * once. Changes before the first turn shown wait for earlier messages to load, so a line never sits above history it
 * came after. */
export function notesBefore(notes: Note[], turns: Turn[], index: number): Note[] {
  if (index === 0) return []
  const after = ended(turns[index - 1]), until = ended(turns[index])
  return notes.filter((note) => note.at > after && note.at <= until)
}

/** The changes since the newest turn, after it. */
export function notesAfter(notes: Note[], turns: Turn[]): Note[] {
  const last = turns.at(-1)
  return last ? notes.filter((note) => note.at > ended(last)) : notes
}
