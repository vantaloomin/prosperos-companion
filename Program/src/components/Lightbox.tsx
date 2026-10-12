import { useEffect, useRef, useState, type KeyboardEvent, type MouseEvent, type TouchEvent } from 'react'
import { ChevronLeft, ChevronRight, Download, X } from 'lucide-react'
import { saveName, stepTo, swipeAction, type Shown } from './lightboxState'

export type { Shown } from './lightboxState'

/**
 * A picture at full size over everything, like a phone's photo viewer: tap outside it, press Escape
 * or drag it down to close; arrows, arrow keys or a sideways swipe move between pictures sent together.
 */
export function Lightbox({ pictures, start = 0, onClose }: { pictures: Shown[]; start?: number; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  const touch = useRef<{ x: number; y: number; fingers: number } | null>(null)
  const [index, setIndex] = useState(start)
  useEffect(() => {
    const element = dialog.current
    const opener = document.activeElement as HTMLElement | null
    element?.showModal()
    return () => { element?.close(); (opener?.isConnected ? opener : document.getElementById('main'))?.focus({ preventScroll: true }) }
  }, [])
  const step = (by: number) => setIndex((current) => stepTo(current, by, pictures.length))
  const shown = pictures[index] ?? pictures[0]
  if (!shown) return null
  const many = pictures.length > 1
  const keys = (event: KeyboardEvent) => {
    if (event.key === 'ArrowRight') step(1)
    else if (event.key === 'ArrowLeft') step(-1)
  }
  // A tap on the dark space around the picture closes it; a tap on the picture or a button does not.
  const outside = (event: MouseEvent) => { if (event.target === event.currentTarget || (event.target as HTMLElement).classList.contains('lightbox-stage')) onClose() }
  const touchStart = (event: TouchEvent) => { touch.current = { x: event.touches[0].clientX, y: event.touches[0].clientY, fingers: event.touches.length } }
  const touchEnd = (event: TouchEvent) => {
    const began = touch.current
    touch.current = null
    // Two fingers are a pinch to zoom, and a zoomed-in picture is being looked around, not swiped.
    if (!began || began.fingers > 1 || (window.visualViewport?.scale ?? 1) > 1.05) return
    const action = swipeAction(event.changedTouches[0].clientX - began.x, event.changedTouches[0].clientY - began.y)
    if (action === 'close') onClose()
    else if (action) step(action === 'next' ? 1 : -1)
  }
  return (
    <dialog ref={dialog} className="lightbox" aria-label={many ? `Picture ${index + 1} of ${pictures.length}` : 'Picture'}
      onClose={onClose} onCancel={onClose} onKeyDown={keys} onClick={outside} onTouchStart={touchStart} onTouchEnd={touchEnd}>
      <div className="lightbox-bar">
        <span className="lightbox-count" aria-live="polite">{many ? `${index + 1} of ${pictures.length}` : ''}</span>
        <a className="lightbox-action" href={shown.src} download={saveName(shown.alt)} aria-label="Save picture"><Download aria-hidden="true" /></a>
        <button type="button" className="lightbox-action" aria-label="Close picture" autoFocus onClick={onClose}><X aria-hidden="true" /></button>
      </div>
      <div className="lightbox-stage">
        <figure className="lightbox-picture">
          <img key={shown.src} src={shown.src} alt={shown.alt} />
          {shown.top && <span className="meme-text meme-top">{shown.top}</span>}
          {shown.bottom && <span className="meme-text meme-bottom">{shown.bottom}</span>}
        </figure>
        {many && <>
          <button type="button" className="lightbox-step lightbox-previous" aria-label="Previous picture" disabled={index === 0} onClick={() => step(-1)}><ChevronLeft aria-hidden="true" /></button>
          <button type="button" className="lightbox-step lightbox-next" aria-label="Next picture" disabled={index === pictures.length - 1} onClick={() => step(1)}><ChevronRight aria-hidden="true" /></button>
        </>}
      </div>
    </dialog>
  )
}
