import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { View } from '../../companion'
import type { Chat, ChatList, Companion } from '../../types'
import { refocus } from '../character/refocus'

export const CHATS_KEY = ['chats']
const EVERY_MS = 30_000

/** Every chat with its unread count, kept fresh while the app is open. */
export function useChats(enabled = true) {
  return useQuery({ queryKey: CHATS_KEY, queryFn: () => api<ChatList>('/chats'), enabled, refetchInterval: EVERY_MS })
}

/**
 * Open a chat. A companion's: they come into focus (every view follows them), then the chat shows. A group's
 * opens as its own view.
 */
export function useOpenChat(go: (view: View) => void) {
  const client = useQueryClient()
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState('')
  const open = useCallback(async (chat: Pick<Chat, 'kind' | 'id'>, isOpen: boolean) => {
    setError('')
    const companionId = chat.id
    if (chat.kind === 'group') { go(`group/${encodeURIComponent(chat.id)}`); return true }
    if (isOpen) { go('conversation'); return true }
    setBusy(companionId)
    try {
      await api<Companion>('/companion/cast/focus', { companion_id: companionId })
      await refocus(client)
      go('conversation')
      return true
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'That chat did not open.')
      return false
    } finally { setBusy(null) }
  }, [client, go])
  return { open, busy, error }
}

/**
 * While the chat is on screen, everything it shows up to `seq` counts as read (chatText.readThrough). A window in the background
 * reads nothing until it is looked at again.
 */
export function useMarkRead(threadId: string, seq: number | null) {
  const client = useQueryClient()
  const sent = useRef<{ thread: string; seq: number } | null>(null)
  const [visible, setVisible] = useState(() => document.visibilityState === 'visible')
  useEffect(() => {
    const sync = () => setVisible(document.visibilityState === 'visible')
    document.addEventListener('visibilitychange', sync)
    return () => document.removeEventListener('visibilitychange', sync)
  }, [])
  useEffect(() => {
    if (!visible || seq === null) return
    const last = sent.current
    if (last && last.thread === threadId && last.seq >= seq) return
    sent.current = { thread: threadId, seq }
    api<ChatList>('/chats/read', { thread_id: threadId, seq })
      .then((list) => client.setQueryData(CHATS_KEY, list))
      .catch(() => { sent.current = last })
  }, [visible, seq, threadId, client])
}
