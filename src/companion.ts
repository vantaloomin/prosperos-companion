import { useQuery } from '@tanstack/react-query'
import { api } from './api'
import type { Companion } from './types'

export type View = 'conversation' | 'today' | 'feed' | 'memories' | 'character' | 'settings'

export const COMPANION_KEY = ['companion']

export function useCompanion() {
  return useQuery({ queryKey: COMPANION_KEY, queryFn: () => api<{ companion: Companion | null }>('/companion').then((data) => data.companion) })
}
