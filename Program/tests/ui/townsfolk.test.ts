import assert from 'node:assert/strict'
import { test } from 'node:test'
import { townMet, townNow, townRole } from '../../src/features/today/townText.ts'

const place = { id: 'claddagh', name: 'The Claddagh Pub', kind: 'bar', neighborhood: 'canton' }

test('a townsperson reads as their role and place', () => {
  assert.equal(townRole({ role: 'bartender', staff: true, place, neighborhood: 'Canton' }), 'Bartender at The Claddagh Pub, Canton')
  assert.equal(townRole({ role: 'regular', staff: false, place, neighborhood: '' }), 'A regular at The Claddagh Pub')
  assert.equal(townRole({ role: 'electrician', kind: 'resident', staff: false, place, neighborhood: 'Canton' }), 'Electrician, lives in Canton')
})

test('meetings are counted', () => {
  assert.match(townMet({ times: 1, last_met: '2026-10-05' }), /^Met once, on (5 October|October 5)\.$/)
  assert.match(townMet({ times: 3, last_met: '2026-10-12' }), /^Crossed paths 3 times, last on (12 October|October 12)\.$/)
})

test('where they are now does not repeat the place', () => {
  assert.equal(townNow({ doing: 'working as the bartender', place: { id: 'claddagh', name: 'The Claddagh Pub' }, mood: 'upbeat' }),
    'Right now: probably working as the bartender at The Claddagh Pub (upbeat).')
  assert.equal(townNow({ doing: 'at their usual spot at The Claddagh Pub', place: { id: 'claddagh', name: 'The Claddagh Pub' }, mood: 'warm' }),
    'Right now: probably at their usual spot at The Claddagh Pub (warm).')
  assert.equal(townNow({ doing: 'asleep', place: null, mood: 'down' }), 'Right now: probably asleep (down).')
})
