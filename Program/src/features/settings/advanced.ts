import { useState } from 'react'

/** "Show advanced settings" is a preference of this browser, like a chat draft: off until the user turns it on. */
export const ADVANCED_KEY = 'companion.advancedSettings'

type Store = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'> | undefined

const storage = (): Store => { try { return window.localStorage } catch { return undefined } }

export function readAdvanced(store: Store): boolean {
  try { return store?.getItem(ADVANCED_KEY) === 'on' } catch { return false }
}

export function writeAdvanced(store: Store, on: boolean) {
  try { if (on) store?.setItem(ADVANCED_KEY, 'on'); else store?.removeItem(ADVANCED_KEY) } catch { /* private window: on for this visit only */ }
}

export function useAdvancedSettings(): [boolean, (on: boolean) => void] {
  const [on, setOn] = useState(() => readAdvanced(storage()))
  return [on, (next: boolean) => { setOn(next); writeAdvanced(storage(), next) }]
}
