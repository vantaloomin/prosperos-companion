import type { Chat } from '../../types'
import { shown } from '../status/statusText.ts'

/** The line under a chat's name: their latest message, or yours with "You: " in front; their status before any. */
export function preview(chat: Pick<Chat, 'last' | 'name' | 'status'>): string {
  if (!chat.last) return shown(chat.status)?.text ?? `Say hi to ${chat.name}.`
  return chat.last.role === 'user' ? `You: ${chat.last.text}` : chat.last.text
}

/** Unread messages in the chats you are not looking at, for the Chats button. */
export function othersUnread(chats: Pick<Chat, 'kind' | 'id' | 'focus' | 'unread'>[], open: OpenChat = null): number {
  return chats.reduce((total, chat) => total + (isOpen(chat, open) ? 0 : chat.unread), 0)
}

/** A badge's number: 1 to 99, then "99+". */
export function badge(count: number): string {
  return count > 99 ? '99+' : String(count)
}

/** For screen readers: "Sally, 2 unread messages". */
export function chatLabel(chat: Pick<Chat, 'kind' | 'id' | 'name' | 'unread' | 'focus'>, open: OpenChat = null): string {
  const parts = [chat.kind === 'group' ? `${chat.name} (group)` : chat.name]
  if (chat.unread) parts.push(`${chat.unread} unread message${chat.unread === 1 ? '' : 's'}`)
  if (isOpen(chat, open)) parts.push('open now')
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

/** Which chat is on screen: a group's while it is open, else the companion in focus. */
export type OpenChat = { kind: string; id: string } | null

export function isOpen(chat: Pick<Chat, 'kind' | 'id' | 'focus'>, open: OpenChat): boolean {
  return open ? chat.kind === open.kind && chat.id === open.id : chat.focus
}

/** Unread messages by kind of chat, for the Profile (companions) and Groups tabs. */
export function unreadOf(chats: Pick<Chat, 'kind' | 'unread'>[], kind: string): number {
  return chats.reduce((total, chat) => total + (chat.kind === kind ? chat.unread : 0), 0)
}
