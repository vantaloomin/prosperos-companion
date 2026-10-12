import { useEffect, useRef, useState, type KeyboardEvent, type MouseEvent, type TouchEvent } from 'react'
import { ChevronLeft, ChevronRight, Download, X } from 'lucide-react'
import { appNow } from '../appTime'
import { clockTime } from '../when'
import { saveName, stepTo, swipeAction, type Shown } from './lightboxState'

export type { Shown } from './lightboxState'

/**
 * A picture at full size over everything, like a phone's photo viewer: tap outside it, press Escape
 * or drag it down to close; arrows, arrow keys or a sideways swipe move between pictures sent together.
 */
export function Lightbox({ pictures, start = 0, onClose }: { pictures: Shown[]; start?: number; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null)
  const close = useRef<HTMLButtonElement>(null)
  const [index, setIndex] = useState(start)
  useEffect(() => {
    const element = dialog.current
    const opener = document.activeElement as HTMLElement | null
    const keyboard = !!opener?.matches(':focus-visible')
    element?.showModal()
    // The modal would otherwise start on Save, its first control. The ring shows only when opened from the keyboard.
    if (close.current) moveFocus(close.current, keyboard)
    return () => { element?.close(); (opener?.isConnected ? opener : document.getElementById('main'))?.focus({ preventScroll: true }) }
  }, [])
  const step = (by: number) => setIndex((current) => stepTo(current, by, pictures.length))
  const swipe = useSwipe(step, onClose)
  const shown = pictures[index] ?? pictures[0]
  if (!shown) return null
  const keys = (event: KeyboardEvent) => {
    if (event.key === 'ArrowRight') step(1)
    else if (event.key === 'ArrowLeft') step(-1)
  }
  // A tap on the dark space around the picture closes it; a tap on the picture or a button does not.
  const outside = (event: MouseEvent) => { if (event.target === event.currentTarget || (event.target as HTMLElement).classList.contains('lightbox-stage')) onClose() }
  return (
    <dialog ref={dialog} className="lightbox" aria-label={`Picture from ${shown.from}`}
      onClose={onClose} onCancel={onClose} onKeyDown={keys} onClick={outside} {...swipe}>
      <div className="lightbox-bar">
        <p className="lightbox-context" aria-live="polite">
          {[shown.from, clockTime(shown.when, appNow()), pictures.length > 1 ? `${index + 1} of ${pictures.length}` : ''].filter(Boolean).join(' · ')}
        </p>
        <a className="lightbox-action" href={shown.src} download={saveName(shown)} aria-label="Save picture"><Download aria-hidden="true" /></a>
        <button type="button" className="lightbox-action" ref={close} aria-label="Close picture" onClick={onClose}><X aria-hidden="true" /></button>
      </div>
      <div className="lightbox-stage">
        <figure className="lightbox-picture">
          <img key={shown.src} src={shown.src} alt={shown.alt} />
          {shown.top && <span className="meme-text meme-top">{shown.top}</span>}
          {shown.bottom && <span className="meme-text meme-bottom">{shown.bottom}</span>}
        </figure>
        {pictures.length > 1 && <Arrows index={index} count={pictures.length} step={step} />}
      </div>
    </dialog>
  )
}

/** Previous and next. The one at an end hides; if it had focus, focus moves to the other so it never falls back to the top bar. */
function Arrows({ index, count, step }: { index: number; count: number; step: (by: number) => void }) {
  const previous = useRef<HTMLButtonElement>(null)
  const next = useRef<HTMLButtonElement>(null)
  const atStart = index === 0
  const atEnd = index === count - 1
  useEffect(() => {
    const active = document.activeElement
    // The ring carries over only when the arrow had it, so a mouse click never shows one.
    const keyboard = !!active?.matches(':focus-visible')
    const other = atEnd && (active === next.current || active === document.body) ? previous.current
      : atStart && (active === previous.current || active === document.body) ? next.current : null
    if (other) moveFocus(other, keyboard)
  }, [atStart, atEnd])
  return <>
    <button ref={previous} type="button" className="lightbox-step lightbox-previous" aria-label="Previous picture" hidden={atStart} onClick={() => step(-1)}><ChevronLeft aria-hidden="true" /></button>
    <button ref={next} type="button" className="lightbox-step lightbox-next" aria-label="Next picture" hidden={atEnd} onClick={() => step(1)}><ChevronRight aria-hidden="true" /></button>
  </>
}

/** Focus moved by the viewer itself shows its ring only for keyboard users; the quiet mark goes when focus leaves. */
function moveFocus(element: HTMLElement, keyboard: boolean) {
  element.classList.toggle('quiet', !keyboard)
  element.addEventListener('blur', () => element.classList.remove('quiet'), { once: true })
  element.focus()
}

/** A sideways swipe steps between pictures and a drag down closes, ignoring pinches and a zoomed-in picture being looked around. */
function useSwipe(step: (by: number) => void, onClose: () => void) {
  const touch = useRef<{ x: number; y: number; fingers: number } | null>(null)
  return {
    onTouchStart: (event: TouchEvent) => { touch.current = { x: event.touches[0].clientX, y: event.touches[0].clientY, fingers: event.touches.length } },
    onTouchEnd: (event: TouchEvent) => {
      const began = touch.current
      touch.current = null
      if (!began || began.fingers > 1 || (window.visualViewport?.scale ?? 1) > 1.05) return
      const action = swipeAction(event.changedTouches[0].clientX - began.x, event.changedTouches[0].clientY - began.y)
      if (action === 'close') onClose()
      else if (action) step(action === 'next' ? 1 : -1)
    },
  }
}
