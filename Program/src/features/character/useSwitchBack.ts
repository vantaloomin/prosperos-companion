import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { View } from '../../companion'
import type { CastDraft, Companion } from '../../types'
import { refocus } from './refocus'

/** Make a companion who stepped back the main character again, then open the chat with them. */
export function useSwitchBack(go: (view: View) => void) {
  const client = useQueryClient()
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState('')
  const switchTo = async (companionId: string) => {
    setBusy(companionId)
    setError('')
    try {
      await api<Companion>('/companion/cast/focus', { companion_id: companionId })
      // Every view showed the other companion's life; start them all from the one now in focus.
      await refocus(client)
      go('conversation')
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'The switch did not happen.')
    } finally { setBusy(null) }
  }
  return { switchTo, busy, error }
}

/** Make a townsperson or a match a companion and the main character from the profile the town gives them, then
 * open the chat ("the world exists outside of User"): the Character page changes anything afterwards. */
export function useStartWith(go: (view: View) => void) {
  const client = useQueryClient()
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState('')
  const startWith = async (key: string) => {
    setBusy(key)
    setError('')
    try {
      const draft = await api<CastDraft>(`/companion/cast/draft?key=${encodeURIComponent(key)}`)
      await api<Companion>('/companion/cast/switch', { key, definition: draft.definition, ties: [] })
      await refocus(client)
      go('conversation')
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'They could not become a companion. Try again.')
    } finally { setBusy(null) }
  }
  return { startWith, busy, error }
}
