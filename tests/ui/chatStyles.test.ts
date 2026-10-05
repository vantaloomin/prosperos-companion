import assert from 'node:assert/strict'
import { test } from 'node:test'
import { CHAT_STYLES, chatStyleOf, soundsOn } from '../../src/features/conversation/chatStyles.ts'
import { availabilityCue } from '../../src/features/conversation/imSounds.ts'

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

test('the door sound marks them coming free and the away sound marks them leaving', () => {
  assert.equal(availabilityCue(undefined, 'free'), null)
  assert.equal(availabilityCue('working', 'free'), 'door')
  assert.equal(availabilityCue('free', 'asleep'), 'away')
  assert.equal(availabilityCue('working', 'out'), null)
  assert.equal(availabilityCue('free', 'free'), null)
})
