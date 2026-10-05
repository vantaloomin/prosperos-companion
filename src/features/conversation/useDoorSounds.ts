import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { Today } from '../../types'
import { availabilityCue, playCue } from './imSounds'

/** Retro IM's door and away sounds follow their availability; the first reading after opening is silent. */
export function useDoorSounds(enabled: boolean) {
  const today = useQuery({ queryKey: ['today'], queryFn: () => api<Today>('/today'), staleTime: 60_000, refetchInterval: 5 * 60_000 })
  const state = today.data?.availability.state
  const previous = useRef(state)
  useEffect(() => {
    const cue = availabilityCue(previous.current, state)
    previous.current = state
    if (enabled && cue) playCue(cue)
  }, [enabled, state])
}
