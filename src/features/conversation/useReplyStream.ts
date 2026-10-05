import { useEffect, useRef } from 'react'
import type { Message } from '../../types'

interface Handlers { onText: (id: string, text: string) => void; onDone: (reply: Message) => void; onLost: (id: string) => void }

/**
 * Follow one reply over server-sent events. A snapshot carries everything written so far, so a
 * reconnect or reload catches up instead of duplicating text. Closing the stream never stops the reply.
 */
export function useReplyStream(id: string, handlers: Handlers) {
  const latest = useRef(handlers)
  useEffect(() => { latest.current = handlers })
  useEffect(() => {
    let text = ''
    let finished = false
    const source = new EventSource(`/api/conversation/replies/${encodeURIComponent(id)}/events`)
    source.addEventListener('snapshot', (event) => { text = JSON.parse((event as MessageEvent).data).text; latest.current.onText(id, text) })
    source.addEventListener('delta', (event) => { text += JSON.parse((event as MessageEvent).data).text; latest.current.onText(id, text) })
    source.addEventListener('done', (event) => { finished = true; source.close(); latest.current.onDone(JSON.parse((event as MessageEvent).data)) })
    // EventSource retries on its own; once it gives up, the saved history is reloaded instead.
    source.onerror = () => { if (!finished && source.readyState === EventSource.CLOSED) latest.current.onLost(id) }
    return () => source.close()
  }, [id])
}
