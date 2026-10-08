import { useEffect, useRef } from 'react'
import { Copy } from 'lucide-react'
import type { Message } from '../../types'
import type { Action } from './useMessageSheet'

function copy(message: Message) {
  void navigator.clipboard?.writeText(message.text).catch(() => undefined)
}

/** The actions of one message in a sheet from the bottom of the screen, under a preview of the message. */
export function MessageSheet({ message, actions, onClose }: { message: Message; actions: Action[]; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  // The finger that opened the sheet is still down; its release must not count as a tap on the sheet or outside it.
  const armed = useRef(false)
  useEffect(() => {
    const element = dialog.current
    const opener = document.activeElement as HTMLElement | null
    element?.showModal()
    return () => { element?.close(); if (opener?.isConnected) opener.focus({ preventScroll: true }) }
  }, [])
  const all: Action[] = message.text.trim() ? [['Copy', <Copy key="icon" aria-hidden="true" />, copy], ...actions] : actions
  const preview = message.text.length > 400 ? `${message.text.slice(0, 400)}…` : message.text
  return (
    <dialog ref={dialog} className={`message-sheet message-sheet-${message.role}`} aria-label="Message actions" onClose={onClose} onCancel={onClose}
      onPointerDown={() => { armed.current = true }}
      onClickCapture={(event) => { if (!armed.current) event.stopPropagation() }}
      onClick={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <div className="sheet-preview" aria-hidden="true">{preview}</div>
      <div className="sheet-group" role="group">
        {all.map(([label, icon, action]) => (
          <button key={label} type="button" className="sheet-action" onClick={() => { onClose(); action(message) }}>{icon}<span>{label}</span></button>
        ))}
      </div>
      <button type="button" className="sheet-action sheet-cancel" onClick={onClose}>Cancel</button>
    </dialog>
  )
}
