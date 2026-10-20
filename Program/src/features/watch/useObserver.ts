import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { Observer, WatchFeed } from '../../types'

export const OBSERVER_KEY = ['observer']

/** Whether the user is just watching this world (companion/observer.py), and who the Watching page follows. */
export function useObserver(enabled = true) {
  return useQuery({ queryKey: OBSERVER_KEY, queryFn: () => api<Observer>('/observer'), enabled })
}

/** The focus's last week, told by the narrator. Real time: it looks again every minute while open. */
export function useWatchFeed(focus: string | undefined) {
  return useQuery({
    queryKey: [...OBSERVER_KEY, 'feed', focus],
    queryFn: () => api<WatchFeed>(`/observer/feed?focus=${encodeURIComponent(focus ?? '')}`),
    enabled: !!focus,
    refetchInterval: 60_000,
  })
}

/** Turn watching on or off, or follow someone else; Matchlight and the worlds list show it too. */
export function useWatchActions() {
  const client = useQueryClient()
  const change = async (body: { watching?: boolean; focus?: string }) => {
    const next = await api<Observer>('/observer', body, 'PUT')
    client.setQueryData(OBSERVER_KEY, next)
    await Promise.all([client.invalidateQueries({ queryKey: ['dating'] }), client.invalidateQueries({ queryKey: ['worlds'] }),
      client.invalidateQueries({ queryKey: [...OBSERVER_KEY, 'feed'] })])
    return next
  }
  return { change }
}
