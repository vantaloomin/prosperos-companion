import { useEffect, useRef } from 'react'
import type { Message } from '../../types'
import type { Phase } from './activity'

interface Handlers { onText: (id: string, text: string) => void; onPhase: (id: string, phase: Phase) => void; onDone: (reply: Message) => void; onLost: (id: string) => void }

/**
 * Follow one reply over server-sent events. A snapshot carries everything written so far, so a
 * reconnect or reload catches up instead of duplicating text. Closing the stream never stops the reply.
 * Phase events say what the app is doing before the text arrives (getting ready, waiting for the model).
 */
export function useReplyStream(id: string, handlers: Handlers) {
  const latest = useRef(handlers)
  useEffect(() => { latest.current = handlers })
  useEffect(() => {
    let text = ''
    let finished = false
    const source = new EventSource(`/api/conversation/replies/${encodeURIComponent(id)}/events`)
    source.addEventListener('snapshot', (event) => {
      const data = JSON.parse((event as MessageEvent).data)
      text = data.text
      latest.current.onText(id, text)
      if (data.phase) latest.current.onPhase(id, data.phase)
    })
    source.addEventListener('phase', (event) => latest.current.onPhase(id, JSON.parse((event as MessageEvent).data).phase))
    source.addEventListener('delta', (event) => { text += JSON.parse((event as MessageEvent).data).text; latest.current.onText(id, text) })
    source.addEventListener('done', (event) => { finished = true; source.close(); latest.current.onDone(JSON.parse((event as MessageEvent).data)) })
    // EventSource retries on its own; once it gives up, the saved history is reloaded instead.
    source.onerror = () => { if (!finished && source.readyState === EventSource.CLOSED) latest.current.onLost(id) }
    return () => source.close()
  }, [id])
}
