import { test } from 'node:test'
import assert from 'node:assert/strict'
import { companionsLine, copyLabel, pausedNote, pausedWhen, copyNote, initial, personaName, personaRef, personaRefTagged, personaSuffix, personaTitle, whereLine, worldTag } from '../../src/features/worlds/worldsText.ts'
import { fromPersona } from '../../src/features/dating/datingText.ts'

test('a persona without a name is never called You', () => {
  assert.equal(personaName({ name: '  ' }), '')
  assert.equal(personaTitle({ name: '' }), 'Your first persona')
  assert.equal(personaRef({ name: '' }), 'this persona')
  assert.equal(personaRef({ name: 'Sam' }), 'Sam')
  assert.equal(initial({ name: 'sam' }), 'S')
  assert.equal(initial({ name: '' }), '')
  assert.equal(whereLine({ name: 'Sam' }, { name: 'Baltimore' }), 'Sam · Baltimore')
  assert.equal(whereLine({ name: '' }, { name: 'Baltimore' }), 'Baltimore')
})

test('a world lists its companions briefly', () => {
  assert.equal(companionsLine({ companions: [] }), 'No companions yet')
  assert.equal(companionsLine({ companions: ['Mira', 'Sally'] }), 'Mira and Sally')
  assert.equal(companionsLine({ companions: ['A', 'B', 'C', 'D', 'E'] }), 'A, B and 3 more')
})

test('Matchlight starts from the persona', () => {
  const profile = fromPersona({ name: 'Sam', gender: 'man', age: 31, about: 'Paramedic.' })
  assert.equal(profile.name, 'Sam')
  assert.equal(profile.age, 31)
  assert.equal(profile.gender, 'man')
  assert.equal(profile.bio, 'Paramedic.')
  assert.equal(fromPersona(null).name, '')
})

test('a copy of a persona says what it takes and what it leaves', () => {
  assert.equal(copyLabel({ name: 'Sam' }), 'Copy Sam to a new world')
  assert.equal(copyLabel({ name: '' }), 'Copy this persona to a new world')
  assert.equal(copyNote({ name: 'Sam' }), 'A second Sam with the same details, starting over in a new world with new people. Your companions and history stay with this Sam, and changing one later leaves the other as it is.')
  assert.match(copyNote({ name: '' }), /^A second persona with the same details.*stay with this persona,/)
})

test('two personas of one name are told apart by their worlds', () => {
  const sam = { id: 'a', name: 'Sam', worlds: [{ name: 'Baltimore' }] }
  const copy = { id: 'b', name: 'Sam ', worlds: [{ name: 'Grandport' }, { name: 'Osaka' }] }
  const jordan = { id: 'c', name: 'Jordan', worlds: [{ name: 'Haddon Harbor' }] }
  const all = [sam, copy, jordan]
  assert.equal(worldTag(sam, all), 'Baltimore')
  assert.equal(worldTag(copy, all), 'Grandport +1')
  assert.equal(worldTag(jordan, all), '')
  assert.equal(personaSuffix(true, 'Baltimore'), 'you, now · Baltimore')
  assert.equal(personaSuffix(false, 'Grandport'), 'Grandport')
  assert.equal(personaSuffix(true, ''), 'you, now')
  assert.equal(personaSuffix(false, ''), '')
  assert.equal(personaRefTagged(copy, 'Grandport +1'), 'Sam (Grandport +1)')
  assert.equal(personaRefTagged(jordan, ''), 'Jordan')
})

test('a world the user left says it is paused, since when, and what going back does', () => {
  const now = new Date(2026, 9, 31, 14, 0)
  assert.equal(pausedNote({ active: true, paused: false }, now), null)
  assert.equal(pausedNote({ active: false, paused: true, paused_since: new Date(2026, 9, 30, 9).toISOString(), catches_up: true }, now),
    'Since Oct 30. Life there waits for you and catches up a little when you go back.')
  assert.equal(pausedNote({ active: false, paused: true, paused_since: null, catches_up: false }, now),
    'Life there waits for you and picks up where it left off.')
  assert.equal(pausedNote({ active: true, paused: true, paused_in_settings: true, paused_since: new Date(2026, 9, 31, 9, 5).toISOString() }, now),
    'Paused in Settings since 9:05 AM. Nothing happens here until you resume, and that time is skipped.')
  assert.equal(pausedWhen(new Date(2025, 11, 2).toISOString(), now), 'Dec 2, 2025')
})
