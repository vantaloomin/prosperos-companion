import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import { TOGETHER_KEY, type Together } from './outingText'

/** Outings with the user and the companion's trips (GET /api/life/outings), shared by Today and the chat strip. */
export function useTogether() {
  return useQuery({ queryKey: TOGETHER_KEY, queryFn: () => api<Together>('/life/outings'), refetchInterval: 60_000 })
}
