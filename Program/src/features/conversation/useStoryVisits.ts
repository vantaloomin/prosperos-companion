import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { StoryVisit } from '../../types'

const NONE: StoryVisit[] = []

/** The companion's finished visits in the Story, each a line in their chat where it happened
 * (companion/story_visits.py). */
export function useStoryVisits(): StoryVisit[] {
  return useQuery({ queryKey: ['story-visits'], queryFn: () => api<{ visits: StoryVisit[] }>('/story/visits') }).data?.visits ?? NONE
}
