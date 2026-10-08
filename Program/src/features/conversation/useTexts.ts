import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { HISTORY_KEY } from '../../companion'
import type { TextCheck } from '../../types'
import { CHATS_KEY } from '../chats/useChats'

const EVERY_MS = 60_000

/**
 * While the app is open, ask once a minute whether a companion sends a first message. The
 * backend decides the triggers and every limit; a sent message just refreshes the conversation.
 */
export function useTexts(enabled: boolean) {
  const client = useQueryClient()
  useEffect(() => {
    if (!enabled) return
    let running = false
    const tick = async () => {
      if (running) return
      running = true
      try {
        const result = await api<TextCheck>('/life/texts/check', {})
        if (!result.message) return
        // Any companion may write first; the open chat reloads only when it was theirs.
        void client.invalidateQueries({ queryKey: CHATS_KEY })
        if (result.focus !== false) void client.invalidateQueries({ queryKey: HISTORY_KEY })
      } catch { /* The next tick tries again. */ } finally { running = false }
    }
    void tick()
    const timer = window.setInterval(() => void tick(), EVERY_MS)
    return () => window.clearInterval(timer)
  }, [enabled, client])
}
