import { useSyncExternalStore } from 'react'
import { WIDTHS, clampWidth } from './chatText'

/**
 * How the chat list beside the chat is laid out on this device: hidden or shown, and how wide the side lists
 * are. Kept in this browser only, like a window size.
 */
const COLLAPSED = 'companion.chatList.collapsed'
const WIDTH = 'companion.chatList.width'
const listeners = new Set<() => void>()

function read(key: string): string | null {
  try { return localStorage.getItem(key) } catch { return null }
}

function write(key: string, value: string) {
  try { localStorage.setItem(key, value) } catch { /* Still changes for this visit. */ }
  memory.set(key, value)
  listeners.forEach((listener) => listener())
}

const memory = new Map<string, string>()
const value = (key: string) => memory.get(key) ?? read(key)

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}

export function useChatListCollapsed(): [boolean, (collapsed: boolean) => void] {
  const collapsed = useSyncExternalStore(subscribe, () => value(COLLAPSED) === '1', () => false)
  return [collapsed, (next) => write(COLLAPSED, next ? '1' : '0')]
}

export function useChatListWidth(kind: string): [number, (width: number) => void] {
  const stored = useSyncExternalStore(subscribe, () => value(`${WIDTH}.${kind}`), () => null)
  const width = stored ? clampWidth(kind, Number(stored)) : (WIDTHS[kind] ?? WIDTHS.list).start
  return [width, (next) => write(`${WIDTH}.${kind}`, String(clampWidth(kind, next)))]
}
