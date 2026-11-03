import { useEffect, useRef, useState, type FocusEvent, type PointerEvent as ReactPointerEvent, type ReactNode } from 'react'
import { CircleHelp } from 'lucide-react'
import { useFitOnScreen } from './fitOnScreen'

/** How long a tip stays after the pointer leaves, so crossing the gap between the button and its text keeps it. */
const LINGER_MS = 200

interface Props { id: string; label: string; text: string; above?: boolean }

/**
 * A small "?" next to a label with a sentence or two of extra detail. It opens on hover, on keyboard
 * focus and on click or tap, and Escape closes it. The text stays in the page, so the field it explains
 * can list `id` in its aria-describedby and screen readers hear it without opening anything.
 */
export function InfoTip({ id, label, text, above }: Props) {
  return <Tip id={id} text={text} above={above} buttonClass="info-tip-button" buttonLabel={`More about ${label}`}><CircleHelp aria-hidden="true" /></Tip>
}

/**
 * A slider step's word ("True to life") that shows the step's longer explanation the same way a "?" does: at once
 * on hover, on click or tap, and with Enter or Space. It replaces the browser's own tooltip, which only came after
 * the mouse held still and often not at all. Tabbing onto it doesn't open it, so moving through a long page of
 * sliders stays quiet. The text follows the slider, so it changes if the slider moves while it is open.
 */
export function StepTip({ id, label, word, text }: { id: string; label: string; word: string; text: string }) {
  return <Tip id={id} text={text} buttonClass="row-value step-tip-button" buttonLabel={`${label}: ${word}. What this means`} openOnFocus={false}>{word}</Tip>
}

interface TipProps { id: string; text: string; above?: boolean; buttonClass: string; buttonLabel: string; openOnFocus?: boolean; children: ReactNode }

function Tip({ id, text, above, buttonClass, buttonLabel, openOnFocus = true, children }: TipProps) {
  const [pinned, setPinned] = useState(false)
  const [hovered, setHovered] = useState(false)
  const [focused, setFocused] = useState(false)
  const box = useRef<HTMLSpanElement>(null)
  const tip = useRef<HTMLSpanElement>(null)
  const button = useRef<HTMLButtonElement>(null)
  const leaving = useRef<number | undefined>(undefined)
  const open = pinned || hovered || focused
  useFitOnScreen(tip, open)
  useEffect(() => () => window.clearTimeout(leaving.current), [])
  useEffect(() => {
    if (!open) return
    const close = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      // Escape hands focus back to the button when it was inside the tip's box, so the keyboard user stays put.
      if (box.current?.contains(document.activeElement)) button.current?.focus()
      setPinned(false); setHovered(false); setFocused(false)
    }
    const outside = (event: PointerEvent) => { if (!box.current?.contains(event.target as Node)) { setPinned(false); setHovered(false) } }
    document.addEventListener('keydown', close)
    document.addEventListener('pointerdown', outside)
    return () => { document.removeEventListener('keydown', close); document.removeEventListener('pointerdown', outside) }
  }, [open])
  // Hover follows a mouse only: a tap on a phone fires a pretend mouseenter too, which would fight the click's toggle.
  const enter = (event: ReactPointerEvent) => { if (event.pointerType !== 'mouse') return; window.clearTimeout(leaving.current); setHovered(true) }
  const leave = (event: ReactPointerEvent) => {
    if (event.pointerType !== 'mouse') return
    window.clearTimeout(leaving.current)
    leaving.current = window.setTimeout(() => setHovered(false), LINGER_MS)
  }
  // Only keyboard focus opens it: a click or tap focuses the button too, and that open would outlast a second click.
  const keyboardFocus = (event: FocusEvent<HTMLButtonElement>) => { if (openOnFocus && event.currentTarget.matches(':focus-visible')) setFocused(true) }
  // A click while hovering pins the tip open; one more click (or a tap anywhere else) closes it.
  const toggle = () => setPinned((value) => !value)
  return (
    <span ref={box} className={above ? 'info-tip above' : 'info-tip'} onPointerEnter={enter} onPointerLeave={leave}>
      <button ref={button} type="button" className={buttonClass} aria-label={buttonLabel} aria-describedby={id} aria-expanded={open}
        onClick={toggle} onFocus={keyboardFocus} onBlur={() => { setFocused(false); setPinned(false) }}>
        {children}
      </button>
      <span ref={tip} id={id} role="tooltip" className="info-tip-text" hidden={!open}>{text}</span>
    </span>
  )
}
