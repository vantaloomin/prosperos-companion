import { useEffect, useRef } from 'react'
import type { Message } from '../../types'
import type { Phase } from './activity'

interface Handlers { onText: (id: string, text: string) => void; onPhase: (id: string, phase: Phase) => void; onDone: (reply: Message) => void; onLost: (id: string) => void }
interface Source { readonly readyState: number; onerror: ((event: Event) => void) | null; addEventListener(name: string, listener: (event: MessageEvent) => void): void; close(): void }

const CLOSED = 2  // EventSource.CLOSED

/** How long to wait before following a reply again after its stream was lost, by attempt (milliseconds). */
export function followAgainIn(attempt: number): number {
  return Math.min(1000 * 2 ** attempt, 15000)
}

/**
 * Follow one reply over server-sent events until it is done; returns a function that stops following.
 * A snapshot carries everything written so far, so a reconnect catches up instead of duplicating text.
 * EventSource retries on its own; once it gives up, the saved history is reloaded (onLost), and while that
 * still shows the reply being written the reply is followed again, so one that lands later still shows.
 */
export function followReply(id: string, handlers: () => Handlers, open: (url: string) => Source = (url) => new EventSource(url)): () => void {
  let text = ''
  let finished = false
  let lost = 0
  let source: Source
  let timer: ReturnType<typeof setTimeout> | undefined
  const follow = () => {
    source = open(`/api/conversation/replies/${encodeURIComponent(id)}/events`)
    source.addEventListener('snapshot', (event) => {
      lost = 0
      const data = JSON.parse(event.data)
      text = data.text
      handlers().onText(id, text)
      if (data.phase) handlers().onPhase(id, data.phase)
    })
    source.addEventListener('phase', (event) => handlers().onPhase(id, JSON.parse(event.data).phase))
    source.addEventListener('delta', (event) => { text += JSON.parse(event.data).text; handlers().onText(id, text) })
    source.addEventListener('done', (event) => { finished = true; source.close(); handlers().onDone(JSON.parse(event.data)) })
    source.onerror = () => {
      if (finished || source.readyState !== CLOSED) return
      handlers().onLost(id)
      timer = setTimeout(follow, followAgainIn(lost++))
    }
  }
  follow()
  return () => { clearTimeout(timer); source.close() }
}

/** Follow one reply while it is on screen. Closing the stream never stops the reply. Phase events say what the
 * app is doing before the text arrives (getting ready, waiting for the model). */
export function useReplyStream(id: string, handlers: Handlers) {
  const latest = useRef(handlers)
  useEffect(() => { latest.current = handlers })
  useEffect(() => followReply(id, () => latest.current), [id])
}
