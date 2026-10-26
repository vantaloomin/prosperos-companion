import { useRef, type KeyboardEvent, type ReactNode, type PointerEvent, type RefObject } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { keepHeight, setFolded, sizeBox, useFolded, useKeptHeight } from './messageBox'

const STEP = 24

/** The message box's frame: the text box itself is `children`, with `text` its ref. */
export function MessageBox({ text, folded, children }: { text: RefObject<HTMLTextAreaElement | null>; folded: boolean; children: ReactNode }) {
  return <div className={folded ? 'message-box folded' : 'message-box'}>
    <MessageBoxControls text={text} />
    {children}
  </div>
}

/** On the message box's top edge (messageBox.ts): a grip to pull it taller or shorter, and a button that folds it
 * to one line to see more of the chat. */
function MessageBoxControls({ text }: { text: RefObject<HTMLTextAreaElement | null> }) {
  const folded = useFolded()
  return <>
    {!folded && <HeightGrip text={text} />}
    <button type="button" className="message-box-fold" aria-pressed={folded} onClick={() => setFolded(!folded)}
      aria-label={folded ? 'Open the message box' : 'Fold the message box to one line'} title={folded ? 'Open the message box' : 'Fold to one line'}>
      {folded ? <ChevronUp aria-hidden="true" /> : <ChevronDown aria-hidden="true" />}
    </button>
  </>
}

function HeightGrip({ text }: { text: RefObject<HTMLTextAreaElement | null> }) {
  const kept = useKeptHeight()
  const start = useRef<{ y: number; height: number } | null>(null)
  const resize = (height: number) => { if (text.current) keepHeight(sizeBox(text.current, height)) }
  const down = (event: PointerEvent<HTMLDivElement>) => {
    if (!text.current) return
    event.preventDefault()
    event.currentTarget.setPointerCapture(event.pointerId)
    start.current = { y: event.clientY, height: text.current.offsetHeight }
  }
  const move = (event: PointerEvent<HTMLDivElement>) => {
    if (start.current) resize(start.current.height + start.current.y - event.clientY)
  }
  const key = (event: KeyboardEvent<HTMLDivElement>) => {
    const height = text.current?.offsetHeight ?? 0
    if (event.key === 'ArrowUp') resize(height + STEP)
    else if (event.key === 'ArrowDown') resize(height - STEP)
    else if (event.key === 'Home') keepHeight(0)
    else return
    event.preventDefault()
  }
  const end = () => { start.current = null }
  return (
    <div className="message-box-grip" role="separator" aria-orientation="horizontal" tabIndex={0} aria-valuenow={kept}
      aria-label="Message box height. Drag up or press the up arrow to make it taller; double-click or press Home to fit the text again."
      title="Drag to resize. Double-click to fit the text."
      onPointerDown={down} onPointerMove={move} onPointerUp={end} onPointerCancel={end} onDoubleClick={() => keepHeight(0)} onKeyDown={key} />
  )
}
