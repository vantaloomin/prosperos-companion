import assert from 'node:assert/strict'
import { test } from 'node:test'
import { PROFILE_TABS, circleText, handle, profileClass, profileTab, showsCard } from '../../src/features/profile/profileText.ts'

test('the profile holds Messages, Posts and Character under their old addresses', () => {
  assert.deepEqual(PROFILE_TABS.map((tab) => [tab.id, tab.label]), [['conversation', 'Messages'], ['feed', 'Posts'], ['character', 'Character']])
  assert.equal(profileTab('conversation'), 'conversation')
  assert.equal(profileTab('feed'), 'feed')
  assert.equal(profileTab('portraits'), 'character')
  assert.equal(profileTab('appearance'), 'character')
  assert.equal(profileTab('cast/abc'), 'character')
  assert.equal(profileTab('today'), null)
  assert.equal(profileTab('settings/models'), null)
})

test('the card shows above Posts and Character, and Messages keeps only the tabs', () => {
  assert.equal(showsCard('feed'), true)
  assert.equal(showsCard('character'), true)
  assert.equal(showsCard('conversation'), false)
  assert.equal(showsCard('portraits'), false)
})

test('the screen name comes from their name', () => {
  assert.equal(handle('Kimberly Smith'), '@kimberly.smith')
  assert.equal(handle('  Zoë  O\'Neil '), '@zoe.o.neil')
  assert.equal(handle('—'), '')
})

test('the profile takes the chat style, and the dark window only in Retro IM', () => {
  assert.equal(profileClass('community', true), 'profile profile-community')
  assert.equal(profileClass('retro', false), 'profile profile-retro')
  assert.equal(profileClass('retro', true), 'profile profile-retro retro-dark')
})

test('the circle count reads naturally', () => {
  assert.equal(circleText(1), '1 person in their circle')
  assert.equal(circleText(12), '12 people in their circle')
})
