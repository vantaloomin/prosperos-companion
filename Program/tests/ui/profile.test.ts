import assert from 'node:assert/strict'
import { test } from 'node:test'
import { howText, modelHow } from '../../src/features/memories/pairText.ts'
import { profileTabs, circleText, handle, placeFact, profileClass, profileTab, showsCard } from '../../src/features/profile/profileText.ts'

test('the profile holds Messages, Posts, Memories and Character under their old addresses', () => {
  assert.deepEqual(profileTabs().map((tab) => [tab.id, tab.label]), [['conversation', 'Messages'], ['feed', 'Posts'], ['memories', 'Memories'], ['character', 'Character']])
  assert.equal(profileTab('memories'), 'memories')
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
  assert.equal(showsCard('memories'), false)
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

test('the card says long distance, the city and the time difference when they live in another city', () => {
  assert.equal(placeFact('Lisbon, Portugal', { state: 'apart', kind: 'long-distance', text: 'Long distance, Lisbon, 5 hours ahead' }), 'Long distance, Lisbon, 5 hours ahead')
  assert.equal(placeFact('Baltimore, Maryland', { state: 'apart', kind: 'apart', text: '' }), 'Baltimore, Maryland')
  assert.equal(placeFact('Lisbon, Portugal', { state: 'together', kind: 'staying', text: 'Staying with you until Sunday' }), 'Lisbon, Portugal')
  assert.equal(placeFact('Baltimore, Maryland', null), 'Baltimore, Maryland')
})

test('a rough patch says things are tense, and what about only with moods shown', async () => {
  const { ROUGH_PATCH_LEVELS, roughPatchLine } = await import('../../src/features/profile/roughPatchText.ts')
  const closed = { open: false, id: null, text: '', since: null, about: null, small: false }
  assert.equal(roughPatchLine(undefined), '')
  assert.equal(roughPatchLine(closed), '')
  const tense = { open: true, id: 'p1', text: 'Things are a bit tense', since: '2026-10-05', about: null, small: false }
  assert.equal(roughPatchLine(tense), 'Things are a bit tense')
  assert.equal(roughPatchLine({ ...tense, about: 'over what you said: "go away"' }), 'Things are a bit tense over what you said: "go away"')
  assert.equal(roughPatchLine({ ...tense, about: 'they called off dinner at the last minute' }), 'Things are a bit tense: they called off dinner at the last minute')
  assert.equal(ROUGH_PATCH_LEVELS.length, 4)
  for (const level of ROUGH_PATCH_LEVELS) assert.doesNotMatch(level.hint, /\b(?:she|he|her|him|his)\b/i)
})

test('how two companions know each other says you, not the user, on screen', () => {
  assert.equal(howText('Both live in Baltimore, but only know each other through the user'), 'Both live in Baltimore, but only know each other through you')
  assert.equal(howText('Only know each other through the user'), 'Only know each other through you')
  assert.equal(howText("The user's old roommates"), 'Your old roommates')
  assert.equal(howText('Roommates in college'), 'Roommates in college')
  assert.equal(howText('Met at the username meetup'), 'Met at the username meetup')
})

test('the Groups backstory box shows you and saves the user, as the companions read it', () => {
  const suggested = 'Both live in Baltimore, but only know each other through the user'
  assert.equal(howText(suggested), 'Both live in Baltimore, but only know each other through you')
  assert.equal(modelHow(howText(suggested)), suggested)
  assert.equal(modelHow('Your old roommates, they met at your party'), "The user's old roommates, they met at the user's party")
  assert.equal(modelHow("Friends of yours, and you're still in touch"), "Friends of the user's, and you're still in touch")
  assert.equal(modelHow('Roommates in college'), 'Roommates in college')
  assert.equal(modelHow('Met at a youth hostel in Lyon'), 'Met at a youth hostel in Lyon')
})
