import { useQuery } from '@tanstack/react-query'
import { api } from './api'
import type { Companion, WorkspaceSettings } from './types'

export type View = 'conversation' | 'today' | 'feed' | 'memories' | 'character' | 'appearance' | 'settings'

export const COMPANION_KEY = ['companion']
export const HISTORY_KEY = ['conversation']
export const MEMORIES_KEY = ['memories']
export const TIMELINES_KEY = ['timelines']

export function useCompanion() {
  return useQuery({ queryKey: COMPANION_KEY, queryFn: () => api<{ companion: Companion | null }>('/companion').then((data) => data.companion) })
}

export const SETTINGS_KEY = ['settings']

export function useWorkspaceSettings() {
  return useQuery({ queryKey: SETTINGS_KEY, queryFn: () => api<WorkspaceSettings>('/settings') })
}
