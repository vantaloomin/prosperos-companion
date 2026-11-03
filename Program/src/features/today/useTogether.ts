import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import { TOGETHER_KEY, awayTrips, type Together } from './outingText'

/** Outings with the user and the companion's trips (GET /api/life/outings), shared by Today and the chat strip. */
export function useTogether() {
  return useQuery({ queryKey: TOGETHER_KEY, queryFn: () => api<Together>('/life/outings'), refetchInterval: 60_000 })
}

/** The trip away together under way, and those coming up (Today's Now card and Coming up). */
export function useAwayTrips() {
  return awayTrips(useTogether().data?.trips ?? [])
}
