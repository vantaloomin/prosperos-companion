/** The one author's note of a chat (companion/authors_note.py): `companion:<id>`, `group:<id>` or `story`. */
export interface AuthorsNoteState { chat: string; text: string; enabled: boolean; updated_at: string | null }
export const NOTE_LIMIT = 1000

export const noteKey = (chat: string) => ['authors-note', chat]

export type Look = 'off' | 'on' | 'paused'
export function noteLook(text: string, enabled: boolean): Look {
  return !text.trim() ? 'off' : enabled ? 'on' : 'paused'
}
