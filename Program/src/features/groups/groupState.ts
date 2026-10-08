import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { CastMember } from '../../types'

export const GROUPS_KEY = ['groups']
export const CAST_KEY = ['companion-cast']

export const SECRETS_KEY = ['secrets']

export const chatKey = (id: string) => ['group', id]

/** Every companion in the workspace, the main character first: who can be in a group. */
export function useCast() {
  return useQuery({ queryKey: CAST_KEY, queryFn: () => api<{ members: CastMember[] }>('/companion/cast') })
}
