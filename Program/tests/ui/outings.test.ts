import assert from 'node:assert/strict'
import test from 'node:test'
import { outNow, outNowText, outingNote, outingTitle, outingWhen, placeLine, shown, tripDays, tripTitle, undoText, type Outing, type Trip } from '../../src/features/today/outingText.ts'

const outing: Outing = {
  id: 'o1', local_date: '2026-10-08', at_time: '19:00', until_time: '21:00', activity: 'dinner', asked_date: null,
  place: { id: 'ouzo-bay', name: 'Ouzo Bay', kind: 'restaurant', neighborhood: 'Harbor East', summary: '', cost: '$$$', cuisine: 'greek', city: 'Baltimore' },
  named: false, cost: 48, cost_text: 'You paid about $48.', state: 'planned', rolls: 0, ended_at: null, undo: false,
}
const trip: Trip = {
  id: 't1', start_date: '2026-10-17', end_date: '2026-10-18', city_id: 'new-york', city_name: 'New York', kind: 'getaway',
  company: { id: 'p1', name: 'Dana', role: 'sister' }, landmark: { name: 'The High Line', summary: '' }, sunny: false,
  cost_text: '$520', state: 'planned', postcard_message_id: null,
}

test('an outing reads as what, where and when, with who picked the place', () => {
  assert.equal(outingTitle(outing), 'Dinner at Ouzo Bay')
  assert.equal(placeLine(outing.place), 'Greek restaurant in Harbor East')
  assert.match(outingWhen(outing, 'Mira'), /^Thu, Oct 8, 7:00/)
  assert.match(outingWhen({ ...outing, asked_date: '2026-10-06' }, 'Mira'), /\(Tue, Oct 6 didn't work for Mira\)$/)
  assert.equal(outingNote(outing, 'Mira'), '')
  assert.equal(outingNote({ ...outing, named: true }, 'Mira'), 'You picked the place.')
  assert.equal(outingNote({ ...outing, rolls: 1 }, 'Mira'), 'You asked for somewhere else.')
  assert.equal(placeLine({ ...outing.place, kind: 'bar', cuisine: 'irish-pub', neighborhood: 'Canton' }), 'Irish pub in Canton')
  assert.equal(outingNote({ ...outing, state: 'done' }, 'Mira'), 'Mira paid about $48.')
})

test('trips read as days and who they go with', () => {
  assert.equal(tripDays(trip), 'Sat, Oct 17 – Sun, Oct 18')
  assert.equal(tripTitle(trip), 'A weekend in New York with Dana')
  assert.equal(tripTitle({ ...trip, end_date: '2026-10-19', company: null }), 'A long weekend in New York')
  assert.equal(tripTitle({ ...trip, kind: 'family', company: { id: 'p2', name: 'Rosa', role: 'mother' } }), 'Visiting Rosa in New York')
})

test('the chat strip shows only an outing under way, and called-off ones leave Today', () => {
  assert.equal(outNow({ outings: [outing], trips: [] }), null)
  const now = { ...outing, state: 'now' as const }
  assert.equal(outNow({ outings: [outing, now], trips: [] }), now)
  assert.match(outNowText(now, 'Mira'), /^Out with Mira at Ouzo Bay until 9:00/)
  assert.deepEqual(shown([outing, { ...outing, id: 'o2', state: 'cancelled' }]).map((item) => item.id), ['o1'])
  // Just called off, or just headed home: collapsed with Undo.
  const off = { ...outing, id: 'o3', state: 'cancelled' as const, undo: true }
  assert.deepEqual(shown([off]).map((item) => item.id), ['o3'])
  assert.equal(undoText(off), 'Called off.')
  const home = { ...outing, state: 'done' as const, undo: true }
  assert.equal(undoText(home), 'Headed home.')
  assert.equal(outNow({ outings: [home], trips: [] }), home)
  assert.equal(undoText(outing), '')
})
