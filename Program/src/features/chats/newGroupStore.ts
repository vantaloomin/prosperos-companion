import { useSyncExternalStore } from 'react'

/**
 * Whether the New group dialog is open, and who starts ticked. It opens from the Chats list's + menu and from a
 * chat's ⋯ menu, and App.tsx hosts it once (NewGroupHost.tsx), so there is no Groups page to go through.
 */
type State = { open: boolean; chosen?: string[] }
let state: State = { open: false }
const listeners = new Set<() => void>()

function set(next: State) {
  state = next
  listeners.forEach((listener) => listener())
}

export function openNewGroup(chosen?: string[]) {
  set({ open: true, chosen })
}

export function closeNewGroup() {
  set({ open: false })
}

export function useNewGroup(): State {
  return useSyncExternalStore((listener) => { listeners.add(listener); return () => { listeners.delete(listener) } }, () => state, () => state)
}
