import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import { CHAT_STYLES, chatStyleOf, retroDarkOn, soundsOn } from '../../src/features/conversation/chatStyles.ts'

test('the chat keeps the Feed style until another is saved', () => {
  assert.equal(chatStyleOf(undefined), 'feed')
  assert.equal(chatStyleOf({}), 'feed')
  assert.equal(chatStyleOf({ chat_style: 'bubbles' }), 'bubbles')
  assert.deepEqual(CHAT_STYLES.map((style) => style.id), ['feed', 'bubbles', 'community', 'retro', 'novel'])
})

test('sounds play only in Retro IM, and only once turned on', () => {
  assert.equal(soundsOn({ chat_style: 'retro', chat_sounds: false }), false)
  assert.equal(soundsOn({ chat_style: 'bubbles', chat_sounds: true }), false)
  assert.equal(soundsOn({ chat_style: 'retro', chat_sounds: true }), true)
})

test('the dark window applies only to Retro IM, and only once turned on', () => {
  assert.equal(retroDarkOn({ chat_style: 'retro' }), false)
  assert.equal(retroDarkOn({ chat_style: 'community', chat_retro_dark: true }), false)
  assert.equal(retroDarkOn({ chat_style: 'retro', chat_retro_dark: true }), true)
})

test('a long status line in the Retro IM buddy list never widens the list past its window', () => {
  const css = readFileSync(new URL('../../src/styles.css', import.meta.url), 'utf8')
  assert.match(css, /\.side-buddies ul \{ grid-template-columns: minmax\(0, 1fr\); \}/)
})

test('the chat list beside a chat (feed, bubbles, novel) never grows wider than its own column', () => {
  const css = readFileSync(new URL('../../src/styles.css', import.meta.url), 'utf8')
  assert.match(css, /\.side-list ul \{ grid-template-columns: minmax\(0, 1fr\); \}/)
})
