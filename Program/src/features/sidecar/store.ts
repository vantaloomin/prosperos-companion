/** Shared sidecar state: whether it is open, a reply the user pointed it at, and the character form while one is
 * open, so the sidecar's character changes land in the form rather than a saved version. */
import { useSyncExternalStore } from 'react'
import type { CharacterDefinition, Message } from '../../types'
import type { FormState } from '../character/drafting'
import type { Turn } from './proposals'
import { closeWindow, current, openWindow } from './popout.ts'

export interface FormBridge { form: FormState; setForm: (form: FormState) => void; definition: () => CharacterDefinition }
/** `turns` is the sidecar's conversation: it lasts while the app is open, is never stored and never reaches the companion. */
/** `handed` holds out-of-character asides from the chat (src/features/conversation/ooc.ts) for the sidecar to answer. */
/** `waiting` marks an aside handed over while it stayed closed (a phone) or its window was in the background, for a
 * dot on its button. `mode` is where it opens: docked beside the app, or in its own window (popout.ts). `blocked`
 * is set once when the browser blocked that window and it opened docked instead. */
export type SidecarMode = 'docked' | 'window'
export interface SidecarState {
  open: boolean; focus: Pick<Message, 'id' | 'text'> | null; bridge: FormBridge | null; turns: Turn[]; handed: string[]; waiting: boolean
  mode: SidecarMode; blocked: boolean
}

/** The companion the sidecar's conversation is about; another one coming into focus starts it over. */
let about: string | null = null
/** Set by putBack until the docked panel's composer has taken focus. */
let returning = false

const OPEN_KEY = 'companion:sidecar'
const MODE_KEY = 'companion:sidecar-mode'
const BLOCKED_KEY = 'companion:sidecar-blocked'
// A window never opens by itself on load (the browser would block it), so a remembered window starts closed.
let state: SidecarState = { open: readOpen() && readMode() === 'docked', focus: null, bridge: null, turns: [], handed: [], waiting: false, mode: readMode(), blocked: false }
const listeners = new Set<() => void>()

function readOpen(): boolean {
  try { return localStorage.getItem(OPEN_KEY) === 'open' } catch { return false }
}

function readMode(): SidecarMode {
  try { return localStorage.getItem(MODE_KEY) === 'window' ? 'window' : 'docked' } catch { return 'docked' }
}

function saveMode(mode: SidecarMode) {
  try { localStorage.setItem(MODE_KEY, mode) } catch { /* It opens docked next time. */ }
}

/** The browser blocked the window: open docked, and say why once per session. */
function blockedNow() {
  let told = false
  try { told = sessionStorage.getItem(BLOCKED_KEY) === 'yes'; sessionStorage.setItem(BLOCKED_KEY, 'yes') } catch { /* Say it. */ }
  set({ mode: 'docked', blocked: !told })
  saveMode('docked')
}

function set(change: Partial<SidecarState>) {
  state = { ...state, ...change }
  listeners.forEach((listener) => listener())
}

export const sidecar = {
  get: () => state,
  subscribe(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener) } },
  setOpen(open: boolean) {
    if (!open && state.mode === 'window') closeWindow()
    set({ open, ...(open ? { waiting: false } : { focus: null }) })
    try { localStorage.setItem(OPEN_KEY, open ? 'open' : 'closed') } catch { /* A blocked store only forgets the choice. */ }
  },
  /** Open it where it last was: its own window (focused if already open), else docked. */
  show() {
    if (state.mode === 'window') {
      if (openWindow()) { set({ open: true, waiting: false }); return }
      blockedNow()
    }
    sidecar.setOpen(true)
  },
  /** Into its own window, from the docked panel's Pop out button. */
  popOut() {
    if (!openWindow()) { blockedNow(); return }
    saveMode('window')
    set({ mode: 'window', open: true, waiting: false, blocked: false })
  },
  /** Back beside the app from its window. */
  putBack() {
    returning = true
    saveMode('docked')
    set({ mode: 'docked' })
    closeWindow()
    sidecar.setOpen(true)
  },
  /** Its window was closed (the window's own close button): the sidecar is closed, and opens there next time. */
  windowClosed() { if (state.mode === 'window' && state.open) sidecar.setOpen(false) },
  /** Whether the docked panel just came back from its window, so its composer takes focus (once). */
  takeReturning(): boolean { const was = returning; returning = false; return was },
  setWaiting(waiting: boolean) { if (state.waiting !== waiting) set({ waiting }) },
  /** Open the sidecar on one of the companion's replies. */
  ask(message: Pick<Message, 'id' | 'text'>) { set({ focus: { id: message.id, text: message.text } }); sidecar.show() },
  clearFocus() { set({ focus: null }) },
  /** An out-of-character aside from the chat: the sidecar answers it as if typed there, once open. */
  handOff(text: string, open: boolean) {
    const windowed = state.mode === 'window' && !!current()
    set({ handed: [...state.handed, text], waiting: windowed ? !current()!.document.hasFocus() : !open && !state.open })
    if (open && !windowed) sidecar.show()
  },
  /** The next handed-off aside, taken off the list. */
  takeHanded(): string | undefined {
    const [next, ...rest] = state.handed
    if (next !== undefined) set({ handed: rest })
    return next
  },
  setBridge(bridge: FormBridge | null) { set({ bridge }) },
  setTurns(turns: Turn[]) { set({ turns }) },
  /** What it proposed about one companion (a memory, their reply, a field) never lands on another. */
  follow(companionId: string | null) {
    if (companionId === about) return
    const first = about === null
    about = companionId
    if (!first && (state.turns.length || state.focus)) set({ turns: [], focus: null })
  },
}

export function useSidecar(): SidecarState {
  return useSyncExternalStore(sidecar.subscribe, sidecar.get, sidecar.get)
}

/** Only whether it is open, for the app shell: the shell must not re-render when the form registers itself. */
export function useSidecarOpen(): boolean {
  const open = () => state.open
  return useSyncExternalStore(sidecar.subscribe, open, open)
}

/** Whether an aside waits in the closed sidecar, for the dot on its button. */
export function useSidecarWaiting(): boolean {
  const waiting = () => state.waiting && (!state.open || state.mode === 'window')
  return useSyncExternalStore(sidecar.subscribe, waiting, waiting)
}

/** Where it opens, for the app shell. */
export function useSidecarMode(): SidecarMode {
  const mode = () => state.mode
  return useSyncExternalStore(sidecar.subscribe, mode, mode)
}
