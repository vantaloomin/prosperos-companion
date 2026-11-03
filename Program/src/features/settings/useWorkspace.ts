import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { SETTINGS_KEY, useWorkspaceSettings } from '../../companion'
import { api } from '../../api'
import type { WorkspaceSettings as Settings } from '../../types'

export type Save = (change: Partial<Settings> & { review_complete?: boolean }) => Promise<boolean>

/**
 * The workspace settings and a way to change them, shared by the sections on several Settings tabs.
 * Toggles show the new state at once and fall back to the saved state if the change is refused.
 */
export function useWorkspace() {
  const client = useQueryClient()
  const settings = useWorkspaceSettings()
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<Partial<Settings>>({})
  const save: Save = async (change) => {
    setPending((current) => ({ ...current, ...change }))
    try {
      const saved = await api<Settings>('/settings', change, 'PUT')
      // Holding the saved values locally avoids a flicker before the shared cache re-renders. Only
      // the changed ones: other tabs' sections save the rest, and a stale copy here would hide them.
      setPending((current) => ({ ...current, ...pick(saved, change) }))
      client.setQueryData(SETTINGS_KEY, saved)
      setError(null)
      return true
    } catch (failure) {
      setPending({})
      setError(failure instanceof Error ? failure.message : 'That setting was not saved.')
      return false
    }
  }
  const data = settings.data ? { ...settings.data, ...pending } : null
  const problem = error ?? (settings.isError ? settings.error.message : null)
  return { data, save, setError, setPending, problem }
}

function pick(saved: Settings, change: Partial<Settings>): Partial<Settings> {
  return Object.fromEntries(Object.keys(change).filter((key) => key in saved).map((key) => [key, saved[key as keyof Settings]]))
}

