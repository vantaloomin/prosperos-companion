import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { View } from '../../companion'
import type { Companion } from '../../types'
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
