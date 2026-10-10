import assert from 'node:assert/strict'
import { test } from 'node:test'
import { shown, statusLabel, stickHint } from '../../src/features/status/statusText.ts'
import { preview } from '../../src/features/chats/chatText.ts'

test('the away line shows while they are away, else their status', () => {
  assert.deepEqual(shown({ text: 'coffee first', set_by: 'app', away: { text: 'at work till 6', glyph: 'briefcase' } }), { text: 'at work till 6', away: 'briefcase' })
  assert.deepEqual(shown({ text: 'coffee first', set_by: 'app', away: null }), { text: 'coffee first', away: null })
  assert.equal(shown(null), null)
  assert.equal(statusLabel('Maya', { text: 'zzz', set_by: 'app', away: null }), "Maya's status: zzz")
  assert.equal(statusLabel('Maya', undefined), '')
  assert.match(stickHint('Maya'), /^Stays until something big happens in Maya's life\./)
})

test('a chat with no messages yet shows their status instead of the last message', () => {
  const status = { text: 'payday 💸', set_by: 'app' as const, away: null }
  assert.equal(preview({ name: 'Maya', last: null, status }), 'payday 💸')
  assert.equal(preview({ name: 'Maya', last: null }), 'Say hi to Maya.')
  assert.equal(preview({ name: 'Maya', last: { role: 'companion', text: 'hey', at: '' }, status }), 'hey')
})
