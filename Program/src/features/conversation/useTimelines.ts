import { useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { TIMELINES_KEY } from '../../companion'
import type { TimelineList } from '../../types'
import { waitingDraft } from './timelineText'
import type { DraftState } from './useDraft'

export function useTimelines() {
  return useQuery({ queryKey: TIMELINES_KEY, queryFn: () => api<TimelineList>('/timelines'), staleTime: 30_000 })
}

/** Choosing a timeline changes what every view shows, so everything is fetched again. */
export function useSwitchTimeline() {
  const client = useQueryClient()
  return async (id: string) => {
    const result = await api<TimelineList>(`/timelines/${id}/activate`, {})
    client.setQueryData(TIMELINES_KEY, result)
    await client.invalidateQueries()
    return result
  }
}

/** The current timeline's name when it is an alternate one. A historical edit's waiting words are
 * placed in the message box, and taken out again, unsent, if the user switches away. */
export function useCurrentTimeline(draft: DraftState, onSwitch: () => void) {
  const timelines = useTimelines()
  const current = timelines.data?.timelines.find((timeline) => timeline.active)
  const waiting = waitingDraft(current, draft.value.text)
  const previous = useRef(current)
  useEffect(() => { if (waiting) draft.edit(waiting) }, [waiting]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    const left = previous.current
    previous.current = current
    if (!left || !current || left.id === current.id) return
    if (left.draft && draft.value.text === left.draft) draft.clear()
    onSwitch()
  }, [current?.id]) // eslint-disable-line react-hooks/exhaustive-deps
  return current?.parent_id ? current.label : null
}
