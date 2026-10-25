import { test } from 'node:test'
import assert from 'node:assert/strict'
import { companionsLine, copyLabel, copyNote, initial, personaName, personaRef, personaTitle, whereLine } from '../../src/features/worlds/worldsText.ts'
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
  assert.match(copyNote({ name: 'Sam' }), /^A second Sam, with everything on their form but where they live/)
  assert.match(copyNote({ name: '' }), /^A second persona, with everything on this persona's form/)
  assert.match(copyNote({ name: 'Sam' }), /the other stays as it is\.$/)
})
