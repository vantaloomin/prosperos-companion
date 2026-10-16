import assert from 'node:assert/strict'
import { test } from 'node:test'
import { shown, spoken, statusLabel, stickHint, whereGlyph } from '../../src/features/status/statusText.ts'
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

test('Retro IM decorations are not read aloud', () => {
  assert.equal(spoken('♫ now playing: Mr. Brightside - The Killers ♫'), 'now playing: Mr. Brightside - The Killers')
  assert.equal(spoken('~*~ i\'m fine. ~*~'), "i'm fine.")
  assert.equal(spoken('xXx bleh xXx'), 'bleh')
  assert.equal(spoken('rain on the window, rain in my heart </3'), 'rain on the window, rain in my heart broken heart')
  assert.equal(spoken('i <3 my friends'), 'i love my friends')
  assert.equal(spoken('*pokes you*'), '*pokes you*')
  assert.equal(statusLabel('Maya', { text: '♪ Yellow - Coldplay ♪', set_by: 'app', away: null }), "Maya's status: Yellow - Coldplay")
})

test('the chat list shows luggage on a weekend visit, a phone on a call, else a pin', () => {
  assert.equal(whereGlyph({ state: 'together', kind: 'staying', text: 'Staying with you until Sunday' }), 'luggage')
  assert.equal(whereGlyph({ state: 'together', kind: 'hosting', text: "You're staying in London until Monday" }), 'luggage')
  assert.equal(whereGlyph({ state: 'together', kind: 'home', text: 'Home together' }), 'home')
  assert.equal(whereGlyph({ state: 'call', kind: 'call', text: 'On a call' }), 'phone')
  assert.equal(whereGlyph({ state: 'apart', kind: 'long-distance', text: 'Long distance, London, 5 hours ahead' }), 'pin')
  assert.equal(whereGlyph(null), 'pin')
})
