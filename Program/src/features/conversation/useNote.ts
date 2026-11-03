import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { saveNote } from './noteApi'
import { noteKey, type AuthorsNoteState } from './noteState'

const SAVE_AFTER_MS = 600

/** The note as typed, saved a moment after typing stops (and at once for the switch, Clear and closing). */
export function useNote(chat: string) {
  const client = useQueryClient()
  const stored = useQuery({ queryKey: noteKey(chat), queryFn: () => api<AuthorsNoteState>(`/authors-notes/${chat}`) })
  const [draft, setDraft] = useState<{ text: string; enabled: boolean } | null>(null)
  const [error, setError] = useState<unknown>(null)
  const timer = useRef<number | undefined>(undefined)
  const pending = useRef<{ text: string; enabled: boolean } | null>(null)
  const write = () => {
    window.clearTimeout(timer.current)
    const value = pending.current
    if (!value) return
    pending.current = null
    saveNote(chat, value.text, value.enabled).then((saved) => {
      setError(null)
      client.setQueryData(noteKey(chat), saved)
      // Saved as typed: the stored note shows again (so a change the sidecar applies later shows too), unless more
      // was typed while it saved.
      if (!pending.current) setDraft(null)
    }, setError)
  }
  // Leaving the chat saves what was typed (each chat mounts its own note: `key` is the chat).
  useEffect(() => () => write(), []) // eslint-disable-line react-hooks/exhaustive-deps
  const change = (text: string, enabled: boolean, now = false) => {
    setDraft({ text, enabled })
    pending.current = { text, enabled }
    window.clearTimeout(timer.current)
    if (now) write(); else timer.current = window.setTimeout(write, SAVE_AFTER_MS)
  }
  const shown = draft ?? stored.data ?? { text: '', enabled: true }
  return { text: shown.text, enabled: shown.enabled, change, flush: write, error }
}
