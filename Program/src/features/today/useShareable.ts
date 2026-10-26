import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { ShareablePerson } from '../../types'

/** People in the other companions' circles the open companion could know too (companion/life/shared_people.py). */
export function useShareable(): ShareablePerson[] {
  return useQuery({ queryKey: ['circle', 'shareable'], queryFn: () => api<ShareablePerson[]>('/life/circle/shareable') }).data ?? []
}
