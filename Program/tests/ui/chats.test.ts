import assert from 'node:assert/strict'
import { test } from 'node:test'
import { badge, chatLabel, chatsButtonLabel, clampWidth, isOpen, othersUnread, preview, readThrough, unreadOf } from '../../src/features/chats/chatText.ts'

test('a chat shows their latest message, or yours with "You:"', () => {
  assert.equal(preview({ name: 'Sally', last: { role: 'companion', text: 'Lunch?', at: '2026-10-08T12:00:00Z' } }), 'Lunch?')
  assert.equal(preview({ name: 'Sally', last: { role: 'user', text: 'Sure', at: '2026-10-08T12:00:00Z' } }), 'You: Sure')
  assert.equal(preview({ name: 'Sally', last: null }), 'Say hi to Sally.')
})

test('the Chats button counts only what waits in the other chats', () => {
  const chats = [{ kind: 'companion', id: 'm', focus: true, unread: 3 }, { kind: 'companion', id: 's', focus: false, unread: 2 },
    { kind: 'group', id: 'g', focus: false, unread: 4 }]
  assert.equal(othersUnread(chats), 6)
  // In a group chat, the group is the open one and the companion in focus counts again.
  assert.equal(othersUnread(chats, { kind: 'group', id: 'g' }), 5)
  assert.equal(isOpen(chats[0], { kind: 'group', id: 'g' }), false)
  assert.equal(unreadOf(chats, 'companion'), 5)
  assert.equal(unreadOf(chats, 'group'), 4)
  assert.equal(chatsButtonLabel(2), 'Chats, 2 unread')
  assert.equal(chatsButtonLabel(0), 'Chats')
  assert.equal(badge(7), '7')
  assert.equal(badge(140), '99+')
  assert.equal(chatLabel({ kind: 'companion', id: 's', name: 'Sally', unread: 1, focus: false }), 'Sally, 1 unread message')
  assert.equal(chatLabel({ kind: 'companion', id: 'm', name: 'Mira', unread: 0, focus: true }), 'Mira, open now')
  assert.equal(chatLabel({ kind: 'group', id: 'g', name: 'Book club', unread: 2, focus: false }, { kind: 'group', id: 'g' }),
    'Book club (group), 2 unread messages, open now')
})

test('a chat is read up to their newest message on screen, not a held one', () => {
  const now = Date.parse('2026-10-08T12:00:00Z')
  assert.equal(readThrough([
    { seq: 1, role: 'companion', status: 'complete' },
    { seq: 2, role: 'user', status: 'complete' },
    { seq: 3, role: 'companion', status: 'complete', held_until: '2026-10-08T13:00:00Z' },
    { seq: 4, role: 'companion', status: 'streaming' },
  ], now), 1)
  assert.equal(readThrough([{ seq: 5, role: 'companion', status: 'complete', held_until: '2026-10-08T11:00:00Z' }], now), 5)
  assert.equal(readThrough([], now), null)
})

test('a side list is kept between its narrowest and widest', () => {
  assert.equal(clampWidth('list', 100), 200)
  assert.equal(clampWidth('list', 999), 420)
  assert.equal(clampWidth('cast', 210.4), 210)
  assert.equal(clampWidth('unknown', 50), 200)
})
