import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import { ERA_WORDS_KEY, MODERN_WORDS, type EraWords, type EraWordsView } from './eraWords'

function useEraView(): EraWordsView | undefined {
  return useQuery({ queryKey: ERA_WORDS_KEY, queryFn: () => api<EraWordsView>('/world/words'), staleTime: 5 * 60_000 }).data
}

/** The words where the user lives (eraWords.ts); today's words until they arrive or if they can't load. */
export function useEraWords(): EraWords {
  return useEraView()?.words ?? MODERN_WORDS
}

/** Whether calls are magic here: in a fantasy town talking at a distance is a scrying glass or a speaking stone, so
 * a call shows a glint of magic (Sparkles) instead of the telephone handset (Iris, 2026-10-21). */
export function useMagicCalls(): boolean {
  return useEraView()?.group === 'fantasy'
}
