import assert from 'node:assert/strict'
import { test } from 'node:test'
import { badge, chatLabel, chatsButtonLabel, othersUnread, preview, readThrough } from '../../src/features/chats/chatText.ts'

test('a chat shows their latest message, or yours with "You:"', () => {
  assert.equal(preview({ name: 'Sally', last: { role: 'companion', text: 'Lunch?', at: '2026-10-08T12:00:00Z' } }), 'Lunch?')
  assert.equal(preview({ name: 'Sally', last: { role: 'user', text: 'Sure', at: '2026-10-08T12:00:00Z' } }), 'You: Sure')
  assert.equal(preview({ name: 'Sally', last: null }), 'Say hi to Sally.')
})

test('the Chats button counts only what waits in the other chats', () => {
  assert.equal(othersUnread([{ focus: true, unread: 3 }, { focus: false, unread: 2 }, { focus: false, unread: 0 }]), 2)
  assert.equal(chatsButtonLabel(2), 'Chats, 2 unread')
  assert.equal(chatsButtonLabel(0), 'Chats')
  assert.equal(badge(7), '7')
  assert.equal(badge(140), '99+')
  assert.equal(chatLabel({ name: 'Sally', unread: 1, focus: false }), 'Sally, 1 unread message')
  assert.equal(chatLabel({ name: 'Mira', unread: 0, focus: true }), 'Mira, open now')
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
