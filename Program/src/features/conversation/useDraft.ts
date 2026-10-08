import { useState } from 'react'
import { DRAFT_KEY, editDraft, newDraft, pictureDraft, readDraft, writeDraft, type Draft, type DraftPicture } from './draft'

const storage = () => { try { return window.localStorage } catch { return undefined } }

/** `key` is where the unsent message is kept; each chat has its own. */
export function useDraft(key = DRAFT_KEY) {
  const [value, setValue] = useState<Draft>(() => readDraft(storage(), key))
  const [sending, setSending] = useState(false)
  const save = (next: Draft) => { setValue(next); writeDraft(storage(), next, key) }
  return {
    value,
    sending,
    setSending,
    edit: (text: string) => save(editDraft(value, text)),
    setPictures: (pictures: DraftPicture[]) => save(pictureDraft(value, pictures)),
    clear: () => save(newDraft()),
  }
}

export type DraftState = ReturnType<typeof useDraft>
