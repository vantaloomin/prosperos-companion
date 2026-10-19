import assert from 'node:assert/strict'
import test from 'node:test'
import { metText, personNow } from '../../src/features/today/circleText.ts'
import { mapPlace } from '../../src/features/today/todayText.ts'
import { outingTitle, peopleLine, placeLine } from '../../src/features/today/outingText.ts'
import { stripLine, type WhereState } from '../../src/features/conversation/whereText.ts'
import type { CirclePerson } from '../../src/types.ts'

const person = { id: 'p', key: 'k', name: 'Ana', role: 'mom', status: 'active', revision: 0, career: null, employer: null, neighborhood: null, city: null, now: null, recent: [] } as CirclePerson
const met = { met_on: '2026-10-17', before: false, meeting: null, impression: 'warm' as const, warmth: 2, label: 'Liked you right away', consequence_id: null }

test('the circle list says who has met you and what they think', () => {
  assert.equal(metText(person), null)
  assert.match(metText({ ...person, met }) ?? '', /^Met you .+ · Liked you right away$/)
  assert.equal(metText({ ...person, met: { ...met, before: true, met_on: null, label: 'Warmed to you' } }), 'Knows you from way back · Warmed to you')
  // What they think stays unsaid until the evening has happened.
  assert.equal(metText({ ...person, met: { ...met, meeting: 'soon', met_on: null } }), 'Meeting you soon')
  assert.equal(metText({ ...person, met: { ...met, meeting: 'now', met_on: null } }), 'Meeting you now')
  assert.equal(personNow({ ...person, met: { ...met, meeting: 'now', met_on: null } }), 'Right now: meeting you')
  // One line: the month and day never wrap apart.
  assert.match(metText({ ...person, met }) ?? '', /^Met you \S+\u00a0\S+ · /)
})

test('a family dinner says who comes and where', () => {
  const place = { id: '~family', name: "Ana and Rui's place", kind: 'family-home', neighborhood: 'Canton', summary: '', cost: '', cuisine: '', city: 'Baltimore',
    people: [{ id: '1', name: 'Ana', role: 'mom' }, { id: '2', name: 'Rui', role: 'dad' }, { id: '3', name: 'Leo', role: 'brother' }], first: true }
  assert.equal(outingTitle({ activity: 'meet-family', place }), "Family dinner at Ana and Rui's place")
  assert.equal(placeLine(place), 'Family home, Canton')
  assert.equal(peopleLine(place), 'With Ana (mom), Rui (dad) and Leo (brother), meeting you for the first time')
  assert.equal(peopleLine(place, 'planned'), 'With Ana (mom), Rui (dad) and Leo (brother), meeting you for the first time')
  // Once it is over it reads as past.
  assert.equal(peopleLine(place, 'done'), 'With Ana (mom), Rui (dad) and Leo (brother), the first time you met')
  assert.equal(peopleLine({ ...place, people: [place.people[0]], first: false }), 'With Ana (mom)')
  const kids = [{ name: 'Leo', role: 'son, 6' }, { name: 'Maya', role: 'daughter, 3' }]
  assert.equal(peopleLine({ ...place, people: [place.people[0]], kids }),
    'With Leo (son, 6), Maya (daughter, 3) and Ana (mom), meeting you for the first time')
  assert.equal(peopleLine({ ...place, people: undefined }), '')
})

test('the strip names the family home without a map link', () => {
  const place = { id: '~family', name: "Ana and Rui's place", kind: 'family-home', neighborhood: '', summary: '', cost: '', cuisine: '', city: '' }
  const outing = { id: 'o', local_date: '2026-10-18', at_time: '18:30', until_time: '21:30', activity: 'meet-family', asked_date: null, place, named: false, cost: 0, cost_text: '', state: 'now' as const, rolls: 0, ended_at: null, undo: false, not_now: false }
  const where: WhereState = { state: 'together', kind: 'out', text: '', outing }
  const line = stripLine(where, 'Mira')
  assert.equal(line?.place, null)
  assert.match(line?.lead ?? '', /^Together at Ana and Rui's place$/)
})

test('a dinner at their family home has no map link in the day list', () => {
  assert.equal(mapPlace({ id: '~family' }), null)
  assert.equal(mapPlace({ id: '~home' }), null)
  assert.equal(mapPlace({ id: 'berthas' }), 'berthas')
  assert.equal(mapPlace(undefined), null)
})
