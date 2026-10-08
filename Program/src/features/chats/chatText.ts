import type { Chat } from '../../types'

/** The line under a chat's name: their latest message, or yours with "You: " in front. */
export function preview(chat: Pick<Chat, 'last' | 'name'>): string {
  if (!chat.last) return `Say hi to ${chat.name}.`
  return chat.last.role === 'user' ? `You: ${chat.last.text}` : chat.last.text
}

/** Unread messages in the chats you are not looking at, for the Chats button. */
export function othersUnread(chats: Pick<Chat, 'focus' | 'unread'>[]): number {
  return chats.reduce((total, chat) => total + (chat.focus ? 0 : chat.unread), 0)
}

/** A badge's number: 1 to 99, then "99+". */
export function badge(count: number): string {
  return count > 99 ? '99+' : String(count)
}

/** For screen readers: "Sally, 2 unread messages". */
export function chatLabel(chat: Pick<Chat, 'name' | 'unread' | 'focus'>): string {
  const parts = [chat.name]
  if (chat.unread) parts.push(`${chat.unread} unread message${chat.unread === 1 ? '' : 's'}`)
  if (chat.focus) parts.push('open now')
  return parts.join(', ')
}

/** "Chats" with the count waiting elsewhere, for the button's accessible name. */
export function chatsButtonLabel(waiting: number): string {
  return waiting ? `Chats, ${waiting} unread` : 'Chats'
}

/**
 * The newest message of theirs the user can see now, to mark the chat read up to. A held reply whose time
 * has not come is not shown yet (companion/life/pacing.py), so it is not read.
 */
export function readThrough(messages: { seq: number; role: string; status: string; held_until?: string | null }[], now: number): number | null {
  let seq: number | null = null
  for (const message of messages) {
    if (message.role !== 'companion' || message.status !== 'complete') continue
    if (message.held_until && Date.parse(message.held_until) > now) continue
    if (seq === null || message.seq > seq) seq = message.seq
  }
  return seq
}

/** The narrowest and widest a resizable list may be, by style. */
export const WIDTHS: Record<string, { min: number; max: number; start: number }> = {
  list: { min: 200, max: 420, start: 280 },
  cast: { min: 150, max: 280, start: 200 },
  buddies: { min: 150, max: 320, start: 190 },
}

export function clampWidth(kind: string, width: number): number {
  const range = WIDTHS[kind] ?? WIDTHS.list
  return Math.round(Math.min(range.max, Math.max(range.min, width)))
}
