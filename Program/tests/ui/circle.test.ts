import assert from 'node:assert/strict'
import { test } from 'node:test'
import { aboutChange, alsoText, fromText, ageClamp, noteCount, aboutForm, displayName, personFacts, personNow, personTies, personWork, placeWords } from '../../src/features/today/circleText.ts'
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

test('parents who parted in an older city read separated, not divorced', () => {
  assert.equal(personTies(person({ knows: [{ id: 'r', name: 'Rui', how: 'separated' }, { id: 'a', name: 'Ana', how: 'family' }] })),
    'Separated from Rui. Knows Ana (family).')
  assert.equal(personTies(person({ knows: [{ id: 'r', name: 'Rui', how: 'divorced' }] })), 'Divorced from Rui.')
})

test('the edit form starts from the person and sends only what changed', () => {
  const form = aboutForm(person({ pronouns: 'she/her', age: 40, employer: 'Mercy' }))
  assert.deepEqual(form.values, { name: 'Ebony', role: 'friend', pronouns: 'she/her', job: 'Nurse', employer: 'Mercy', age: '40', local: 'here', note: '' })
  assert.deepEqual(aboutChange(form.values, { ...form.values }, false), {})
  assert.deepEqual(aboutChange(form.values, { ...form.values, job: ' ER nurse ', age: '41', local: 'away', name: '' }, false),
    { job: 'ER nurse', age: 41, local: false })
  // A coworker's "Works with Dana" is not offered as a job to edit.
  assert.equal(aboutForm(person({ career: 'Works with Dana', works_with_companion: true })).values.job, '')
})

test('adding someone sends only what was filled in', () => {
  const empty = aboutForm().values
  assert.deepEqual(aboutChange(empty, { ...empty, name: 'Mo', job: 'barista' }, true), { name: 'Mo', job: 'barista' })
  assert.deepEqual(aboutChange(empty, { ...empty, name: 'Mo', local: 'away', age: '30' }, true), { name: 'Mo', age: 30, local: false })
  assert.deepEqual(aboutChange(empty, { ...empty, name: 'Mo', local: 'here' }, true), { name: 'Mo', local: true })
})

test('the age box keeps an age in range and says so, past the most only for their own age', () => {
  assert.deepEqual(ageClamp('', ''), { value: '', note: '' })
  assert.deepEqual(ageClamp('400', '44'), { value: '120', note: 'Kept at 120, the most.' })
  assert.deepEqual(ageClamp('300', '300'), { value: '300', note: '' })
  assert.deepEqual(ageClamp('9', '44'), { value: '16', note: 'Kept at 16, the least.' })
})

test('the note counts only near its limit, and a workplace alone reads as one', () => {
  assert.equal(noteCount('short'), '')
  assert.equal(noteCount('x'.repeat(260)), '260 of 300')
  assert.equal(personWork(person({ career: null, employer: 'Charm City Ink' })), 'Works at Charm City Ink')
})

test('where they live reads aboard and off a ship or station', () => {
  assert.deepEqual(placeWords(), { here: 'In town', away: 'Out of town' })
  assert.deepEqual(placeWords('ship'), { here: 'Aboard the ship', away: 'Off the ship' })
  assert.deepEqual(placeWords('station'), { here: 'On the station', away: 'Off the station' })
  assert.equal(personNow(person({ local: false }), 'ship'), 'Lives off the ship')
  assert.equal(personNow(person({ local: false }), 'station'), 'Lives off the station')
})

test('someone two companions know says so on both sides', () => {
  assert.equal(alsoText(person()), null)
  assert.equal(alsoText(person({ also: [{ companion_id: 's', name: 'Spock', role: 'mother' }] })), "Also Spock's mother")
  assert.equal(alsoText(person({ also: [{ companion_id: 's', name: 'Spock', role: 'mother' }, { companion_id: 'v', name: 'Vorel', role: 'friend' }, { companion_id: 'k', name: 'Kirk', role: 'neighbor' }] })),
    "Also Spock's mother, Vorel's friend and Kirk's neighbor")
  assert.equal(fromText(person({ shared: { owner_id: 'o', owner: 'Sarek', role: 'wife' } })), "From Sarek's life · Sarek's wife")
  assert.equal(fromText(person()), '')
})
