import assert from 'node:assert/strict'
import { test } from 'node:test'
import { displayName, personFacts, personNow, personTies, personWork } from '../../src/features/today/circleText.ts'
import type { CirclePerson } from '../../src/types.ts'

const person = (extra: Partial<CirclePerson> = {}): CirclePerson => ({
  id: 'p', key: 'circle:t:0', name: 'Ebony', role: 'friend', status: 'active', revision: 1, career: 'Nurse', employer: null,
  neighborhood: null, city: 'Baltimore', now: null, recent: [], ...extra,
})

test('facts lead with the relationship and add closeness only when it is not close', () => {
  assert.equal(personFacts(person({ closeness: 'close', pronouns: 'she/her', age: 40 })), 'friend · she/her · 40')
  assert.equal(personFacts(person({ closeness: 'occasional' })), 'friend (occasional)')
})

test('now reads out of town, asleep, a block or free', () => {
  assert.equal(personNow(person({ local: false })), 'Lives out of town')
  const block = { key: 'w', label: 'Registered nurse', kind: 'work', days: [0], start: '09:00', end: '17:00', themes: [] }
  assert.equal(personNow(person({ now: block as CirclePerson['now'] })), 'Right now: Registered nurse')
  assert.equal(personNow(person({ now: { ...block, kind: 'sleep' } as CirclePerson['now'] })), 'Asleep right now')
  assert.equal(personNow(person()), 'Free right now')
})

test('work and name fall back gracefully', () => {
  assert.equal(personWork(person({ employer: 'Mercy Hospital' })), 'Nurse, Mercy Hospital')
  assert.equal(personWork(person({ career: null })), null)
  assert.equal(displayName(person({ full_name: 'Ebony Carter' })), 'Ebony Carter')
  assert.equal(displayName(person()), 'Ebony')
  assert.equal(displayName(person({ name: 'Rowan', full_name: 'Ebony Carter' })), 'Rowan')
})

test('ties name a partner first, then who else they know', () => {
  assert.equal(personTies(person()), null)
  assert.equal(personTies(person({ knows: [{ id: 'a', name: 'Ana', how: 'family' }, { id: 'r', name: 'Rui', how: 'married' }] })),
    'Married to Rui. Knows Ana (family).')
})
