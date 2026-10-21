import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import { ERA_WORDS_KEY, MODERN_WORDS, type EraWords, type EraWordsView } from './eraWords'

/** The words where the user lives (eraWords.ts); today's words until they arrive or if they can't load. */
export function useEraWords(): EraWords {
  const found = useQuery({ queryKey: ERA_WORDS_KEY, queryFn: () => api<EraWordsView>('/world/words'), staleTime: 5 * 60_000 })
  return found.data?.words ?? MODERN_WORDS
}
