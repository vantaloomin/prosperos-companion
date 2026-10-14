import assert from 'node:assert/strict'
import test from 'node:test'
import { inPerson, stripAction, stripLine, type WhereOuting, type WhereState } from '../../src/features/conversation/whereText.ts'
import { shown } from '../../src/features/status/statusText.ts'

const outing: WhereOuting = {
  id: 'o1', local_date: '2026-10-08', at_time: '19:00', until_time: '21:00', activity: 'dinner', asked_date: null,
  place: { id: 'ouzo-bay', name: 'Ouzo Bay', kind: 'restaurant', neighborhood: 'Harbor East', summary: '', cost: '$$$', cuisine: 'greek', city: 'Baltimore' },
  named: false, cost: 48, cost_text: '', state: 'now', rolls: 0, ended_at: null, undo: false, not_now: false,
}
const out: WhereState = { state: 'together', kind: 'out', text: 'Together at Ouzo Bay', outing }
const yours: WhereState = { state: 'together', kind: 'yours', text: 'At your place', outing: { ...outing, activity: 'visit-yours', place: { ...outing.place, id: '~yours', name: 'Your place', kind: 'your-home' } } }

test('the strip says where they are together, until when, and offers the right way out', () => {
  const line = stripLine(out, 'Mira')
  assert.equal(line?.lead, 'Together at ')
  assert.equal(line?.place?.name, 'Ouzo Bay')
  assert.match(line?.tail ?? '', /^ until 9:00/)
  assert.deepEqual(stripAction(out), { action: 'home', label: 'Head home' })
  assert.equal(stripLine(yours, 'Mira')?.lead, 'Mira is at your place')
  assert.deepEqual(stripAction(yours), { action: 'home', label: 'Say goodbye' })
  assert.equal(stripLine({ ...yours, kind: 'theirs' }, 'Mira')?.lead, "At Mira's place")
  const knock: WhereState = { ...yours, kind: 'knock', outing: { ...yours.outing!, not_now: true } }
  assert.equal(stripLine(knock, 'Mira')?.lead, 'Mira dropped by and is at your place')
  assert.deepEqual(stripAction(knock), { action: 'home', label: 'Not now' })
  assert.ok(inPerson(out) && !inPerson({ state: 'apart', kind: 'apart', text: '', outing: null }))
})

test('apart shows no strip, and just after heading home it offers Undo', () => {
  assert.equal(stripLine({ state: 'apart', kind: 'apart', text: '', outing: null }, 'Mira'), null)
  const headed: WhereState = { ...out, state: 'apart', outing: { ...outing, state: 'done', undo: true } }
  assert.equal(stripLine(headed, 'Mira')?.lead, 'Headed home from Ouzo Bay.')
  assert.deepEqual(stripAction(headed), { action: 'undo', label: 'Undo' })
  assert.equal(stripLine({ ...headed, kind: 'yours' }, 'Mira')?.lead, 'Mira headed home.')
})

test('while together, their status line says where', () => {
  const status = { text: 'coffee first', set_by: 'app' as const, away: null, where: { state: 'together' as const, kind: 'yours', text: 'At your place' } }
  assert.deepEqual(shown(status), { text: 'At your place', away: 'pin' })
  assert.deepEqual(shown({ ...status, where: { state: 'apart', kind: 'long-distance', text: 'Long distance, Lisbon' } }), { text: 'coffee first', away: null })
})

test('on a call the strip says with whom and how long, with End call; a ring offers Answer and Decline', async () => {
  const { callActions, callClock, canCall, notTexting } = await import('../../src/features/conversation/whereText.ts')
  const on = { id: 'c1', direction: 'you' as const, status: 'on' as const, started_at: '2026-10-08T19:00:00Z', until_at: '2026-10-08T20:00:00Z', ended_at: null }
  const calling: WhereState = { state: 'call', kind: 'call', text: 'On a call', outing: null, call: on }
  assert.equal(stripLine(calling, 'Mira')?.lead, 'On a call with Mira')
  assert.deepEqual(callActions(on).map((item) => item.label), ['End call'])
  assert.ok(notTexting(calling) && !canCall(calling))
  const ringing: WhereState = { state: 'apart', kind: 'ringing', text: 'Calling you', outing: null, call: { ...on, direction: 'them', status: 'ringing', started_at: null } }
  assert.equal(stripLine(ringing, 'Mira')?.lead, 'Mira is calling')
  assert.deepEqual(callActions(ringing.call).map((item) => item.label), ['Answer', 'Decline'])
  assert.ok(!canCall(ringing) && !notTexting(ringing))
  assert.equal(stripLine({ ...ringing, call: { ...ringing.call!, status: 'missed' } }, 'Mira')?.lead, 'Missed call from Mira.')
  assert.deepEqual(callActions({ ...ringing.call!, status: 'missed' }).map((item) => item.label), ['Call back'])
  assert.equal(stripLine({ ...ringing, call: { ...on, status: 'missed' } }, 'Mira')?.lead, "Mira didn't pick up.")
  const ended = stripLine({ ...ringing, call: { ...on, status: 'ended', ended_at: '2026-10-08T19:12:05Z' } }, 'Mira')
  assert.equal(`${ended?.lead}${ended?.tail}`, 'Call ended · 12:05')
  assert.equal(callClock(3_723_000), '1:02:03')
  assert.ok(canCall({ state: 'apart', kind: 'long-distance', text: 'Long distance, Lisbon', outing: null, call: null }))
})

test('on a call their status line says so', () => {
  const status = { text: 'coffee first', set_by: 'app' as const, away: null, where: { state: 'call' as const, kind: 'call', text: 'On a call' } }
  assert.deepEqual(shown(status), { text: 'On a call', away: 'phone' })
  assert.deepEqual(shown({ ...status, where: { state: 'apart', kind: 'ringing', text: 'Calling you' } }), { text: 'Calling you', away: 'phone' })
})
