import { useLayoutEffect, useRef, useSyncExternalStore } from 'react'

/**
 * The message box grows with what is written, up to its maximum height (styles.css), then scrolls. On a computer
 * its top edge can be pulled up to keep it taller (MessageBoxControls.tsx); the box sits at the bottom of the chat,
 * so the edge that moves is the one you hold. It can also fold down to one line to see more of the chat, and opens
 * again when you click into it. The height is kept in this browser only, like a window size; folding lasts the visit.
 */
const KEY = 'companion.messageBox.height'
const listeners = new Set<() => void>()
let height: number | null = null
let folded = false

function readHeight(): number {
  if (height !== null) return height
  try { return Number(localStorage.getItem(KEY)) || 0 } catch { return 0 }
}

function changed() { listeners.forEach((listener) => listener()) }

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}

/** Keep the box this tall; 0 fits it to the text again. */
export function keepHeight(next: number) {
  height = Math.max(0, Math.round(next))
  folded = false
  try { localStorage.setItem(KEY, String(height)) } catch { /* Still changes for this visit. */ }
  changed()
}

export function setFolded(next: boolean) {
  if (folded === next) return
  folded = next
  changed()
}

export const useKeptHeight = () => useSyncExternalStore(subscribe, readHeight, () => 0)
export const useFolded = () => useSyncExternalStore(subscribe, () => folded, () => false)

/** The height the box takes for its text alone, with `wanted` kept when that is taller (capped at its maximum).
 * Returns the height worth keeping: 0 when the text alone fills it. */
export function sizeBox(element: HTMLTextAreaElement, wanted: number) {
  const tallest = parseFloat(getComputedStyle(element).maxHeight) || Infinity
  const kept = Math.min(wanted, tallest)
  // Measuring shrinks the box for a moment; hold its frame at its height meanwhile, or the chat above grows into the
  // gap, its scroll is cut back, and the newest message ends up hidden behind the box.
  const frame = element.parentElement
  if (frame) frame.style.minHeight = `${frame.offsetHeight}px`
  element.style.height = 'auto'
  const border = element.offsetHeight - element.clientHeight
  const own = element.scrollHeight + border
  element.style.height = `${Math.max(own, kept)}px`
  if (frame) frame.style.minHeight = ''
  return kept > own ? kept : 0
}

/** The box's ref, sized on every change. Folded, or shrunk to one line (`compact`, a phone reading history), it
 * shows the line being written. */
export function useMessageBox(value: string, compact = false) {
  const text = useRef<HTMLTextAreaElement>(null)
  const kept = useKeptHeight()
  const isFolded = useFolded()
  useLayoutEffect(() => {
    const element = text.current
    if (!element) return
    if (isFolded) element.style.height = ''
    else sizeBox(element, kept)
    if (compact || isFolded) element.scrollTop = element.scrollHeight
  }, [value, compact, kept, isFolded])
  return { text, folded: isFolded }
}
