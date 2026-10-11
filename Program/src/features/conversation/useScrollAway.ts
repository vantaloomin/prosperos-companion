import { useCallback, useEffect, useRef, useState, type RefObject } from 'react'

const NEAR_BOTTOM_PX = 80
// Long enough for a smooth scroll to finish; after it a reader who grabbed the history mid-way counts again.
const JUMP_MS = 1000

/** Whether the reader has scrolled up into the history. While they have, the message box shrinks to one line and
 * an arrow offers the way back down (styles.css); on a phone, scrolling up also puts the keyboard away so more of
 * the history shows. `pinnedRef` keeps new text in view only while the reader is already at the bottom. */
export function useScrollAway(transcriptRef: RefObject<HTMLDivElement | null>, pinnedRef: RefObject<boolean>) {
  const [away, setAway] = useState(false)
  // Set while the arrow's smooth scroll runs, so its in-between positions don't shrink the box again.
  const jumpingRef = useRef(false)
  // The last heights seen, so a scroll caused by the layout changing (the keyboard, the box growing, messages that
  // were drawn at an estimated height getting their real one) isn't read as the reader scrolling up.
  const heightRef = useRef(0)
  const contentRef = useRef(0)
  const onScroll = useCallback(() => {
    const element = transcriptRef.current
    if (!element) return
    const resized = element.clientHeight !== heightRef.current || element.scrollHeight !== contentRef.current
    heightRef.current = element.clientHeight
    contentRef.current = element.scrollHeight
    const atBottom = element.scrollHeight - element.scrollTop - element.clientHeight < NEAR_BOTTOM_PX
    if (jumpingRef.current || (resized && pinnedRef.current)) {
      if (atBottom) jumpingRef.current = false
      return
    }
    pinnedRef.current = atBottom
    setAway((before) => {
      if (!before && !atBottom) putKeyboardAway()
      return !atBottom
    })
  }, [transcriptRef, pinnedRef])
  const toLatest = useCallback(() => {
    const element = transcriptRef.current
    element?.scrollTo({ top: element.scrollHeight, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
    jumpingRef.current = true
    window.setTimeout(() => { jumpingRef.current = false }, JUMP_MS)
    pinnedRef.current = true
    setAway(false)
  }, [transcriptRef, pinnedRef])
  // The box growing back (or the keyboard opening) makes the transcript shorter, and messages off screen are drawn at an
  // estimated height until they show (styles.css, content-visibility), so the history grows after the jump to the
  // bottom: stay at the bottom when pinned there.
  useEffect(() => {
    const element = transcriptRef.current
    if (!element || typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(() => { if (pinnedRef.current) element.scrollTop = element.scrollHeight })
    observer.observe(element)
    if (element.firstElementChild) observer.observe(element.firstElementChild)
    return () => observer.disconnect()
  }, [transcriptRef, pinnedRef])
  return { away, onScroll, toLatest }
}

function putKeyboardAway() {
  const box = document.getElementById('composer-text')
  if (box && document.activeElement === box && matchMedia('(hover: none)').matches) box.blur()
}
