import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import { WHERE_KEY, type WhereState } from './whereText'

/** Where the companion in focus is with the user right now (GET /api/life/where), refreshed with the chat. */
export function useWhere() {
  return useQuery({ queryKey: WHERE_KEY, queryFn: () => api<WhereState>('/life/where'), refetchInterval: 60_000 })
}
