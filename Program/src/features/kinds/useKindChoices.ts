import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { KindChoices } from '../../types'

/** What the pickers offer where the open companion lives (companion/world/lifespans.py). */
export function useKindChoices(given?: KindChoices) {
  return useQuery({ queryKey: ['life-kinds'], queryFn: () => api<KindChoices>('/life/kinds'), enabled: !given, staleTime: Infinity }).data ?? given
}
