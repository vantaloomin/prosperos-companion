import { test } from 'node:test'
import assert from 'node:assert/strict'
import { companionsLine, initial, personaName, whereLine } from '../../src/features/worlds/worldsText.ts'
import { fromPersona } from '../../src/features/dating/datingText.ts'

test('a persona without a name is you', () => {
  assert.equal(personaName({ name: '  ' }), 'You')
  assert.equal(initial({ name: 'sam' }), 'S')
  assert.equal(whereLine({ name: 'Sam' }, { name: 'Baltimore' }), 'Sam · Baltimore')
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
