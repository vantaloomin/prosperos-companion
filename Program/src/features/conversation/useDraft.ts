import { useState } from 'react'
import { editDraft, newDraft, readDraft, writeDraft, type Draft } from './draft'

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
    clear: () => save(newDraft()),
  }
}

export type DraftState = ReturnType<typeof useDraft>
