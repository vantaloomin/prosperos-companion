import { useEffect, useRef, useState, type MouseEvent, type PointerEvent, type ReactNode } from 'react'
import type { Message } from '../../types'
import { MessageSheet } from './MessageSheet'

export type Act = (message: Message) => void
/** A label, its icon and what it does. */
export type Action = [string, ReactNode, Act]

const HOLD_MS = 450
const SLOP_PX = 10

/** Phones: press and hold a message, as in Messages, WhatsApp or Google Messages, to open its actions in a sheet
 * from the bottom of the screen. Only touch starts it; a mouse keeps the hover actions (TurnView.tsx). */
export function useMessageSheet(message: Message, actions: Action[]) {
  const [open, setOpen] = useState(false)
  const [pressing, setPressing] = useState(false)
  const timer = useRef<number | undefined>(undefined)
  const start = useRef<{ x: number; y: number } | null>(null)
  const cancel = () => { window.clearTimeout(timer.current); start.current = null; setPressing(false) }
  useEffect(() => () => window.clearTimeout(timer.current), [])
  const available = actions.length > 0
  const press = available ? {
    onPointerDown: (event: PointerEvent) => {
      if (event.pointerType !== 'touch' || (event.target as HTMLElement).closest('button, a, input, textarea, select')) return
      start.current = { x: event.clientX, y: event.clientY }
      setPressing(true)
      timer.current = window.setTimeout(() => {
        cancel()
        navigator.vibrate?.(8)
        setOpen(true)
      }, HOLD_MS)
    },
    // Scrolling or dragging is not a press.
    onPointerMove: (event: PointerEvent) => {
      if (start.current && Math.hypot(event.clientX - start.current.x, event.clientY - start.current.y) > SLOP_PX) cancel()
    },
    onPointerUp: cancel,
    onPointerCancel: cancel,
    // Android's own long-press menu, and iOS text selection, would cover the sheet.
    onContextMenu: (event: MouseEvent) => { if (matchMedia('(hover: none)').matches) event.preventDefault() },
  } : {}
  const sheet = open ? <MessageSheet message={message} actions={actions} onClose={() => setOpen(false)} /> : null
  return { press, pressing, sheet, open: () => setOpen(true), available }
}

