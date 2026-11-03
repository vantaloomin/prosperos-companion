import assert from 'node:assert/strict'
import { test } from 'node:test'
import { chatsTarget, inChats, railCurrent } from '../../src/features/nav/navText.ts'

test('Chats holds the list, every chat, the profile tabs, group chats and Secrets, but not Worlds', () => {
  for (const view of ['chats', 'conversation', 'feed', 'memories', 'character', 'portraits', 'another', 'secrets', 'group/abc']) assert.equal(inChats(view), true, view)
  // Worlds opens from the world avatar, so no tab is lit there (Iris).
  assert.equal(inChats('worlds'), false)
  for (const view of ['today', 'map', 'story', 'dating', 'settings/models']) assert.equal(inChats(view), false, view)
})

test('the Chats tab returns to where the user was, and to the list when tapped inside a chat', () => {
  assert.equal(chatsTarget('today', 'group/abc'), 'group/abc')
  assert.equal(chatsTarget('settings', 'chats'), 'chats')
  assert.equal(chatsTarget('conversation', 'conversation'), 'chats')
  assert.equal(chatsTarget('memories', 'memories'), 'chats')
})

test('the side rail lights Memories on its own and Profile on the other profile tabs', () => {
  assert.equal(railCurrent('conversation', 'memories'), true)
  assert.equal(railCurrent('conversation', 'conversation'), true)
  assert.equal(railCurrent('conversation', 'feed'), true)
  assert.equal(railCurrent('conversation', 'another'), true)
  assert.equal(railCurrent('today', 'map/abc'), true)
  assert.equal(railCurrent('conversation', 'group/abc'), true)
  assert.equal(railCurrent('settings', 'settings/debug'), true)
})
