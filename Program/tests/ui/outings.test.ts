import assert from 'node:assert/strict'
import test from 'node:test'
import { awayNowLine, awayTrips, meetLine, onwardLine, outingNote, outingTitle, outingWhen, placeLine, shown, tripDays, tripTitle, tripTravel, undoText, type Outing, type Trip } from '../../src/features/today/outingText.ts'

const outing: Outing = {
  id: 'o1', local_date: '2026-10-08', at_time: '19:00', until_time: '21:00', activity: 'dinner', asked_date: null,
  place: { id: 'ouzo-bay', name: 'Ouzo Bay', kind: 'restaurant', neighborhood: 'Harbor East', summary: '', cost: '$$$', cuisine: 'greek', city: 'Baltimore' },
  named: false, cost: 48, cost_text: 'You paid about $48.', state: 'planned', rolls: 0, ended_at: null, undo: false,
}
const trip: Trip = {
  id: 't1', start_date: '2026-10-17', end_date: '2026-10-18', city_id: 'new-york', city_name: 'New York', kind: 'getaway',
  company: { id: 'p1', name: 'Dana', role: 'sister' }, landmark: { name: 'The High Line', summary: '' }, sunny: false,
  cost_text: '$520', state: 'planned', postcard_message_id: null, visit: '', undo: false,
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
  assert.equal(placeLine({ ...outing.place, cuisine: 'tex-mex', neighborhood: 'Canton' }), 'Tex-Mex restaurant in Canton')
})

test('trips read as days and who they go with', () => {
  assert.equal(tripDays(trip), 'Sat, Oct 17 – Sun, Oct 18')
  assert.equal(tripTitle(trip), 'A weekend in New York with Dana')
  assert.equal(tripTitle({ ...trip, end_date: '2026-10-19', company: null }), 'A long weekend in New York')
  assert.equal(tripTitle({ ...trip, kind: 'family', company: { id: 'p2', name: 'Rosa', role: 'mother' } }), 'Visiting Rosa in New York')
  // Weekend visits across the distance (companion/life/long_distance.py).
  assert.equal(tripTitle({ ...trip, visit: 'to-you', city_name: 'Baltimore' }, 'Mira'), 'Mira comes to stay with you')
  assert.equal(tripTitle({ ...trip, visit: 'host', city_name: 'Chicago' }, 'Mira'), 'You stay with Mira in Chicago')
})

test('called-off ones leave Today, and visits read as your place or theirs', () => {
  assert.deepEqual(shown([outing, { ...outing, id: 'o2', state: 'cancelled' }]).map((item) => item.id), ['o1'])
  // Just called off, or just headed home: collapsed with Undo.
  const off = { ...outing, id: 'o3', state: 'cancelled' as const, undo: true }
  assert.deepEqual(shown([off]).map((item) => item.id), ['o3'])
  assert.equal(undoText(off), 'Called off.')
  const home = { ...outing, state: 'done' as const, undo: true }
  assert.equal(undoText(home), 'Headed home.')
  assert.equal(undoText(outing), '')
  const yours = { ...outing, activity: 'visit-yours', place: { ...outing.place, id: '~yours', name: 'Your place', kind: 'your-home', neighborhood: 'Canton' } }
  assert.equal(outingTitle(yours), 'A visit at your place')
  assert.equal(placeLine(yours.place), 'Your place in Canton')
})

test('the plan says how meeting up works, with no Go there step', () => {
  assert.match(meetLine({ state: 'planned', until_time: '17:30' }), /^No need to go anywhere\. When it's time, you'll be there together, and the chat turns face to face until 5:30/)
  assert.match(meetLine({ state: 'now', until_time: '17:30' }), /^You're there together until 5:30.PM\.$/)
  assert.equal(meetLine({ state: 'now', until_time: '' }), "You're there together now.")
  assert.equal(meetLine({ state: 'done', until_time: '17:30' }), '')
  assert.equal(meetLine({ state: 'cancelled', until_time: '17:30' }), '')
})

test('a trip away together is named by where it goes and how it gets there', () => {
  const away: Trip = { id: 't9', start_date: '2026-10-16', end_date: '2026-10-18', city_id: 'away:modern:2026:b-lisbon', city_name: 'Lisbon', kind: 'getaway', company: { id: '~you', name: 'you', role: 'the user' }, landmark: null, sunny: true, cost_text: '$900', state: 'planned', postcard_message_id: null, visit: 'together', undo: false, away: { prep: 'in', by: 'plane', hours: 9 } }
  assert.equal(tripTitle(away, 'Mira'), 'Away in Lisbon with Mira')
  assert.equal(tripTravel(away), 'By plane')
  assert.equal(tripTitle({ ...away, city_name: 'the garden deck', away: { prep: 'on', by: 'tram', hours: 1 } }, 'Mira'), 'Away on the garden deck with Mira')
  assert.equal(tripTravel({ ...away, away: { prep: 'on', by: 'tram', hours: 1 } }), '')
})

test('a trip away together under way is the Now line, and coming-up trips are listed apart', () => {
  const base: Trip = { id: 'a', start_date: '2026-11-01', end_date: '2026-11-05', city_id: 'x', city_name: 'Lisbon', kind: 'getaway', company: null, landmark: null, sunny: true, cost_text: '', state: 'now', postcard_message_id: null, visit: 'together', undo: false, away: { prep: 'in', by: 'plane', hours: 9 } }
  assert.equal(awayNowLine(base), 'Away in Lisbon until Thu')
  assert.equal(awayNowLine(null), undefined)
  const found = awayTrips([base, { ...base, id: 'b', state: 'planned' }, { ...base, id: 'c', visit: '' }, { ...base, id: 'd', state: 'cancelled' }])
  assert.equal(found.now?.id, 'a')
  assert.deepEqual(found.coming.map((trip) => trip.id), ['b'])
})

test('moving on: Today says where next, then where they came from', () => {
  const place = { id: 'the-owl-bar', name: 'The Owl Bar', kind: 'bar', neighborhood: 'Mount Vernon', summary: '', cost: '$$', cuisine: '', city: 'Baltimore' }
  assert.match(onwardLine({ state: 'now', next: { place, activity: 'drinks', at: '21:00', asked: false }, came_from: null }), /^Then drinks at The Owl Bar, around 9:00/)
  assert.equal(onwardLine({ state: 'now', next: null, came_from: { name: 'Lupa', activity: 'dinner', neighborhood: '' } }), 'Came over from Lupa.')
  assert.equal(onwardLine({ state: 'planned', next: null, came_from: null }), '')
})
