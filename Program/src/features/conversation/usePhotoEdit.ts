import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { ChatPhoto } from '../../types'
import { isTaking } from './photoState'
import { usePhoto } from './usePhoto'

export interface PhotoEdit {
  photo: ChatPhoto | undefined
  busy: boolean
  error: string
  /** Removed while this chat was open: the frame's place says so, with Undo, until the chat is left. */
  undo: boolean
  canReroll: boolean
  canRemove: boolean
  reroll: () => void
  remove: () => void
  restore: () => void
}

/** A reply's picture made again or taken out of the chat (companion/images/photo_edits.py). One per reply, so its
 * sheet on a phone and the buttons on the picture share whether it is busy, an error and Undo. */
export function usePhotoEdit(messageId: string, initial?: ChatPhoto | null): PhotoEdit {
  const client = useQueryClient()
  const photo = usePhoto(initial ? messageId : null, initial).data
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [undo, setUndo] = useState(false)
  const path = `/images/photos/${encodeURIComponent(messageId)}`
  const run = async (call: () => Promise<ChatPhoto>, removed?: boolean) => {
    setBusy(true)
    setError('')
    try {
      client.setQueryData(['chat-photo', messageId], await call())
      if (removed !== undefined) setUndo(removed)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'That did not work. Please try again.')
    } finally { setBusy(false) }
  }
  const shown = !!photo && !photo.removed
  return {
    photo, busy, error, undo,
    canReroll: shown && photo.status === 'completed',
    canRemove: shown && !isTaking(photo.status),
    reroll: () => void run(() => api<ChatPhoto>(`${path}/reroll`, {})),
    remove: () => void run(() => api<ChatPhoto>(path, undefined, 'DELETE'), true),
    restore: () => void run(() => api<ChatPhoto>(`${path}/restore`, {}), false),
  }
}
