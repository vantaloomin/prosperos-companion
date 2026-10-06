import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { ChatPhoto } from '../../types'
import { isTaking } from './photoState'

/** A reply's photo, kept current while it is being made. Shared by the reply and the Visual novel stage. */
export function usePhoto(messageId: string | null, initial?: ChatPhoto | null) {
  return useQuery({
    queryKey: ['chat-photo', messageId],
    queryFn: () => api<ChatPhoto>(`/images/photos/${encodeURIComponent(messageId ?? '')}`),
    initialData: initial ?? undefined,
    enabled: Boolean(messageId),
    refetchInterval: (query) => isTaking(query.state.data?.status) ? 3000 : false,
  })
}
