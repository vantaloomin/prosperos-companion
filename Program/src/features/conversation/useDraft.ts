import { useState } from 'react'
import { editDraft, newDraft, pictureDraft, readDraft, writeDraft, type Draft, type DraftPicture } from './draft'

const storage = () => { try { return window.localStorage } catch { return undefined } }

export function useDraft() {
  const [value, setValue] = useState<Draft>(() => readDraft(storage()))
  const [sending, setSending] = useState(false)
  const save = (next: Draft) => { setValue(next); writeDraft(storage(), next) }
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
