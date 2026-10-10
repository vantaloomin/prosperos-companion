import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { LifeSettings } from '../../types'

export const LIFE_KEY = ['life-settings']

export type SaveResult = { tone: 'info' | 'error'; text: string } | null

/** The Life settings (/api/life/settings), saved on change, shared by Life & cities and Realism. */
export function useLifeSettings() {
  const client = useQueryClient()
  const settings = useQuery({ queryKey: LIFE_KEY, queryFn: () => api<LifeSettings>('/life/settings') })
  const [pending, setPending] = useState<Partial<LifeSettings>>({})
  const [result, setResult] = useState<SaveResult>(null)
  const save = async (change: Partial<LifeSettings>, done?: string) => {
    setPending((current) => ({ ...current, ...change }))
    try {
      const saved = await api<LifeSettings>('/life/settings', change, 'PUT')
      setPending(saved)
      client.setQueryData(LIFE_KEY, saved)
      void client.invalidateQueries({ queryKey: ['today'] })
      setResult(done ? { tone: 'info', text: done } : null)
      return true
    } catch (error) {
      setResult({ tone: 'error', text: error instanceof Error ? error.message : 'Not saved.' })
      setPending({})
      return false
    }
  }
  const data = settings.data ? { ...settings.data, ...pending } : undefined
  return { settings, data, save, result }
}
