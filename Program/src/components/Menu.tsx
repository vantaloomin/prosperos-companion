import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode, type RefObject } from 'react'
import type { LucideIcon } from 'lucide-react'
import { useFitOnScreen } from './fitOnScreen'

/**
 * The ⋯ and + menus (style guide: secondary actions for one object, or things you add): an icon button that opens a
 * short list. Each item is an icon, a label and an optional quiet value on the right ("off", "2+ companions").
 * Escape, a pick or a click outside closes it; the arrow keys move between items.
 */
export interface MenuItem {
  label: string
  icon?: LucideIcon
  value?: string
  disabled?: boolean
  onSelect: () => void
}

export type MenuEntry = MenuItem | 'separator'

interface MenuProps {
  /** The button's accessible name and tooltip ("More", "New"). */
  label: string
  icon: LucideIcon
  items: MenuEntry[]
  /** Which edge the list lines up with, and whether it opens upward (from the composer). */
  align?: 'start' | 'end'
  up?: boolean
  /** Shown under the items, such as the chat style previews. A button in it closes the menu like an item. */
  footer?: ReactNode
  className?: string
  /** A dot on the button, for something waiting inside. */
  dot?: boolean
  /** Pressing the button leaves focus where it is (the message box), so a phone's keyboard and layout don't jump mid-tap. */
  keepFocus?: boolean
}

export function Menu({ label, icon: Icon, items, align = 'end', up, footer, className, dot, keepFocus }: MenuProps) {
  const [open, setOpen] = useState(false)
  const button = useRef<HTMLButtonElement>(null)
  const panel = useRef<HTMLDivElement>(null)
  useFitOnScreen(panel, open)
  useCloseOutside(open, panel, button, setOpen)
  useEffect(() => { if (open) firstItem(panel.current)?.focus() }, [open])
  // Focus goes back to the button, unless the pick moved it on (a dialog it opened).
  const close = () => {
    const active = document.activeElement
    setOpen(false)
    if (!active || active === document.body || panel.current?.contains(active)) button.current?.focus()
  }
  const onKey = (event: KeyboardEvent) => {
    if (event.key === 'Escape') { event.stopPropagation(); close() } else if (event.key === 'Tab') setOpen(false)
    else moveFocus(event, panel.current)
  }
  const classes = ['menu-pop', align, up && 'up'].filter(Boolean).join(' ')
  return (
    <span className={className ? `menu-anchor ${className}` : 'menu-anchor'} onKeyDown={onKey}>
      <button ref={button} type="button" className="icon-button" aria-label={label} title={label} aria-haspopup="menu" aria-expanded={open} onMouseDown={keepFocus ? (event) => event.preventDefault() : undefined} onClick={() => setOpen(!open)}>
        <Icon aria-hidden="true" />{dot && <span className="nav-dot" aria-hidden="true" />}
      </button>
      {open && <div ref={panel} className={classes} role="menu" aria-label={label} onClick={(event) => { if ((event.target as HTMLElement).closest('button')) close() }}>
        {items.map((entry, index) => entry === 'separator' ? <hr key={`sep-${index}`} className="menu-sep" /> : <MenuButton key={index} item={entry} />)}
        {footer}
      </div>}
    </span>
  )
}

function MenuButton({ item }: { item: MenuItem }) {
  const { label, icon: Icon, value, disabled, onSelect } = item
  return (
    <button type="button" role="menuitem" className="menu-item" disabled={disabled} onClick={onSelect}>
      {Icon && <Icon aria-hidden="true" />}<span className="menu-label">{label}</span>{value && <span className="menu-value">{value}</span>}
    </button>
  )
}

function items(panel: HTMLElement | null): HTMLElement[] {
  return panel ? [...panel.querySelectorAll<HTMLElement>('[role="menuitem"]:not(:disabled), [role="menuitemradio"]:not(:disabled)')] : []
}

function firstItem(panel: HTMLElement | null): HTMLElement | undefined {
  return items(panel)[0]
}

/** Up and down move between the items, wrapping at the ends; Home and End jump to them. */
function moveFocus(event: KeyboardEvent, panel: HTMLElement | null) {
  const list = items(panel)
  if (!list.length) return
  const at = list.indexOf(document.activeElement as HTMLElement)
  const next = { ArrowDown: at + 1, ArrowUp: at - 1, Home: 0, End: list.length - 1 }[event.key]
  if (next === undefined) return
  event.preventDefault()
  list[(next + list.length) % list.length].focus()
}

function useCloseOutside(open: boolean, panel: RefObject<HTMLElement | null>, button: RefObject<HTMLElement | null>, setOpen: (open: boolean) => void) {
  useEffect(() => {
    if (!open) return
    const outside = (event: PointerEvent) => {
      const target = event.target as Node
      if (!panel.current?.contains(target) && !button.current?.contains(target)) setOpen(false)
    }
    document.addEventListener('pointerdown', outside)
    return () => document.removeEventListener('pointerdown', outside)
  }, [open, panel, button, setOpen])
}
