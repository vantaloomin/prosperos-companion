import { useRef, type KeyboardEvent, type PointerEvent } from 'react'
import { PanelLeftClose, PanelRightClose } from 'lucide-react'
import { WIDTHS } from './chatText'
import { useChatListCollapsed } from './layout'

/** Hides the list beside the chat; the Chats button at the top of the chat brings it back. */
export function CollapseButton({ side = 'left' }: { side?: 'left' | 'right' }) {
  const [, setCollapsed] = useChatListCollapsed()
  const Icon = side === 'left' ? PanelLeftClose : PanelRightClose
  return <button type="button" className="icon-button side-collapse" aria-label="Hide the chat list" title="Hide the chat list" onClick={() => setCollapsed(true)}><Icon aria-hidden="true" /></button>
}

/** Drag (or use the arrow keys on) the list's edge to make it wider or narrower. */
export function ResizeHandle({ kind, width, onWidth, side = 'left' }: { kind: string; width: number; onWidth: (width: number) => void; side?: 'left' | 'right' }) {
  const start = useRef<{ x: number; width: number } | null>(null)
  const range = WIDTHS[kind]
  const direction = side === 'left' ? 1 : -1
  const down = (event: PointerEvent<HTMLDivElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId)
    start.current = { x: event.clientX, width }
  }
  const move = (event: PointerEvent<HTMLDivElement>) => {
    if (start.current) onWidth(start.current.width + direction * (event.clientX - start.current.x))
  }
  const key = (event: KeyboardEvent<HTMLDivElement>) => {
    const step = event.shiftKey ? 40 : 10
    if (event.key === 'ArrowLeft') onWidth(width - direction * step)
    else if (event.key === 'ArrowRight') onWidth(width + direction * step)
    else return
    event.preventDefault()
  }
  return (
    <div className={`side-resize side-resize-${side}`} role="separator" aria-orientation="vertical" aria-label="Chat list width" tabIndex={0}
      aria-valuemin={range.min} aria-valuemax={range.max} aria-valuenow={width}
      onPointerDown={down} onPointerMove={move} onPointerUp={() => { start.current = null }} onPointerCancel={() => { start.current = null }} onKeyDown={key} />
  )
}
