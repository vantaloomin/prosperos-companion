import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import { WHERE_KEY, type WhereState } from './whereText'

/** Where the companion in focus is with the user right now (GET /api/life/where), refreshed with the chat, and more
 * often while a call rings or is on so a ring or a quiet line ending shows soon. */
export function useWhere() {
  return useQuery({
    queryKey: WHERE_KEY, queryFn: () => api<WhereState>('/life/where'),
    refetchInterval: (query) => query.state.data?.call && ['on', 'ringing'].includes(query.state.data.call.status) ? 15_000 : 60_000,
  })
}
