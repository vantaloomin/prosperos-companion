import { useRef, type KeyboardEvent } from 'react'
import { Send, Square } from 'lucide-react'
import type { DraftState } from './useDraft'
import { usePrepare } from './usePrepare'

export function Composer({ name, draft, streaming, onSend, onStop }: { name: string; draft: DraftState; streaming: boolean; onSend: () => void; onStop: () => void }) {
  const prepare = usePrepare()
  const text = useRef<HTMLTextAreaElement>(null)
  const canSend = !!draft.value.text.trim() && !draft.sending && !streaming
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      if (canSend) onSend()
    } else if (event.key === 'Escape' && streaming) {
      onStop()
    }
  }
  return (
    <form className="composer" onSubmit={(event) => { event.preventDefault(); if (canSend) onSend() }}>
      <label className="visually-hidden" htmlFor="composer-text">Message {name}</label>
      <textarea ref={text} id="composer-text" rows={2} value={draft.value.text} placeholder={`Message ${name}`} maxLength={40000}
        onChange={(event) => { draft.edit(event.target.value); prepare() }} onKeyDown={onKeyDown} aria-describedby="composer-help" />
      <p id="composer-help" className="visually-hidden">Enter sends, Shift and Enter adds a new line{streaming ? ', Escape stops the reply' : ''}. Unsent text is kept if you leave.</p>
      {/* Send replaces Stop once the reply ends; keep the keyboard in the message box rather than losing focus. */}
      {streaming
        ? <button type="button" className="button" onClick={() => { onStop(); text.current?.focus() }}><Square aria-hidden="true" />Stop</button>
        : <button type="submit" className="button primary" disabled={!canSend}><Send aria-hidden="true" />Send</button>}
    </form>
  )
}
