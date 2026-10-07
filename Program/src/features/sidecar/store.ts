/** Shared sidecar state: whether it is open, a reply the user pointed it at, and the character form while one is
 * open, so the sidecar's character changes land in the form rather than a saved version. */
import { useSyncExternalStore } from 'react'
import type { CharacterDefinition, Message } from '../../types'
import type { FormState } from '../character/drafting'
import type { Turn } from './proposals'

export interface FormBridge { form: FormState; setForm: (form: FormState) => void; definition: () => CharacterDefinition }
/** `turns` is the sidecar's conversation: it lasts while the app is open, is never stored and never reaches the companion. */
export interface SidecarState { open: boolean; focus: Pick<Message, 'id' | 'text'> | null; bridge: FormBridge | null; turns: Turn[] }

const OPEN_KEY = 'companion:sidecar'
let state: SidecarState = { open: readOpen(), focus: null, bridge: null, turns: [] }
const listeners = new Set<() => void>()

function readOpen(): boolean {
  try { return localStorage.getItem(OPEN_KEY) === 'open' } catch { return false }
}

function set(change: Partial<SidecarState>) {
  state = { ...state, ...change }
  listeners.forEach((listener) => listener())
}

export const sidecar = {
  get: () => state,
  subscribe(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener) } },
  setOpen(open: boolean) {
    set({ open, ...(open ? {} : { focus: null }) })
    try { localStorage.setItem(OPEN_KEY, open ? 'open' : 'closed') } catch { /* A blocked store only forgets the choice. */ }
  },
  /** Open the sidecar on one of the companion's replies. */
  ask(message: Pick<Message, 'id' | 'text'>) { set({ focus: { id: message.id, text: message.text } }); sidecar.setOpen(true) },
  clearFocus() { set({ focus: null }) },
  setBridge(bridge: FormBridge | null) { set({ bridge }) },
  setTurns(turns: Turn[]) { set({ turns }) },
}

export function useSidecar(): SidecarState {
  return useSyncExternalStore(sidecar.subscribe, sidecar.get, sidecar.get)
}

/** Only whether it is open, for the app shell: the shell must not re-render when the form registers itself. */
export function useSidecarOpen(): boolean {
  const open = () => state.open
  return useSyncExternalStore(sidecar.subscribe, open, open)
}
