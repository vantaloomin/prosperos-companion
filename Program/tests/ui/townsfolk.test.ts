import assert from 'node:assert/strict'
import { test } from 'node:test'
import { formerly, townLeft, townMet, townNow, townRole } from '../../src/features/today/townText.ts'

const place = { id: 'claddagh', name: 'The Claddagh Pub', kind: 'bar', neighborhood: 'canton' }

test('a townsperson reads as their role and place', () => {
  assert.equal(townRole({ role: 'bartender', staff: true, place, neighborhood: 'Canton' }), 'Bartender at The Claddagh Pub, Canton')
  assert.equal(townRole({ role: 'regular', staff: false, place, neighborhood: '' }), 'A regular at The Claddagh Pub')
  assert.equal(townRole({ role: 'electrician', kind: 'resident', staff: false, place, neighborhood: 'Canton' }), 'Electrician, lives in Canton')
})

test('meetings are counted', () => {
  assert.match(townMet({ times: 1, last_met: '2026-10-05' }), /^Met once, on October 5\.$/)
  assert.match(townMet({ times: 3, last_met: '2026-10-12' }), /^Crossed paths 3 times, last on October 12\.$/)
})

test('where they are now does not repeat the place', () => {
  assert.equal(townNow({ doing: 'working as the bartender', place: { id: 'claddagh', name: 'The Claddagh Pub' }, mood: 'upbeat' }),
    'Right now: probably working as the bartender at The Claddagh Pub (upbeat).')
  assert.equal(townNow({ doing: 'at their usual spot at The Claddagh Pub', place: { id: 'claddagh', name: 'The Claddagh Pub' }, mood: 'warm' }),
    'Right now: probably at their usual spot at The Claddagh Pub (warm).')
  assert.equal(townNow({ doing: 'asleep', place: null, mood: 'down' }), 'Right now: probably asleep (down).')
})

test('someone who left town is spoken of as gone, in the past tense', () => {
  const left = (why: 'moved' | 'new job' | 'retired' | 'passed', day: string) => ({ why, day, text: '' })
  assert.match(townLeft(left('new job', '2027-06-21')), /^Moved away for a new job \(June 2027\)\.$/)
  assert.match(townLeft(left('moved', '2027-12-06')), /^Moved away \(December 2027\)\.$/)
  assert.match(townLeft(left('retired', '2040-02-13')), /^Retired \(February 2040\)\.$/)
  assert.match(townLeft(left('passed', '2040-01-22')), /^Passed away \(January 2040\)\.$/)
  const walters = { id: 'walters', name: 'Walters Art Museum', kind: 'museum', neighborhood: 'mount-vernon' }
  assert.equal(townRole({ role: 'docent', staff: true, place: walters, neighborhood: '', left: left('new job', '2027-06-21') }),
    'Formerly docent at Walters Art Museum')
  assert.equal(townRole({ role: 'regular', staff: false, place, neighborhood: 'Canton', left: left('moved', '2027-06-21') }),
    'Formerly a regular at The Claddagh Pub, Canton')
  assert.equal(townRole({ role: 'electrician', kind: 'resident', staff: false, place, neighborhood: 'Canton', left: left('moved', '2027-06-21') }),
    'Electrician, used to live in Canton')
  assert.equal(formerly('Librarian at Enoch Pratt Light Street Branch'), 'Formerly a librarian')
  assert.equal(formerly('Office clerk'), 'Formerly an office clerk')
})
