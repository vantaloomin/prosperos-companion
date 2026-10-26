import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { CircleHome } from '../../types'

/** Whether the companion lives aboard a ship or station, so "where they live" can say so; null until known. Under
 * the circle's key, so it is read again when the circle changes. */
export function useCircleHome(): CircleHome['aboard'] {
  const home = useQuery({ queryKey: ['circle', 'home'], queryFn: () => api<CircleHome>('/life/circle/home') })
  return home.data?.aboard ?? null
}
