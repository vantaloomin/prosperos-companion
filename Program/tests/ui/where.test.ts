import assert from 'node:assert/strict'
import test from 'node:test'
import { canBeBackAt, canGoBack, canStayLonger, homeLine, inPerson, stripAction, stripLine, type WhereOuting, type WhereState } from '../../src/features/conversation/whereText.ts'
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
  const loud = { ...headed, outing: { ...headed.outing!, place: { ...outing.place, name: 'Power Plant Live!' } } }
  assert.equal(stripLine(loud, 'Mira')?.lead, 'Headed home from Power Plant Live!')
})

test('while together, their status line says where', () => {
  const status = { text: 'coffee first', set_by: 'app' as const, away: null, where: { state: 'together' as const, kind: 'yours', text: 'At your place' } }
  assert.deepEqual(shown(status), { text: 'At your place', away: 'home' })
  assert.deepEqual(shown({ ...status, where: { state: 'apart', kind: 'long-distance', text: 'Long distance, Lisbon' } }), { text: 'coffee first', away: null })
  assert.deepEqual(shown({ ...status, where: { state: 'together', kind: 'staying', text: 'Staying with you until Sunday' } }), { text: 'Staying with you until Sunday', away: 'luggage' })
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
  assert.deepEqual(callActions(ringing.call).map((item) => item.label), ['Decline', 'Answer'])
  assert.ok(!canCall(ringing) && !notTexting(ringing))
  assert.equal(stripLine({ ...ringing, call: { ...ringing.call!, status: 'missed' } }, 'Mira')?.lead, 'Missed call from Mira.')
  assert.deepEqual(callActions({ ...ringing.call!, status: 'missed' }).map((item) => item.label), ['Call back'])
  assert.equal(stripLine({ ...ringing, call: { ...on, status: 'missed' } }, 'Mira')?.lead, "Mira didn't pick up.")
  const ended = stripLine({ ...ringing, call: { ...on, status: 'ended', ended_at: '2026-10-08T19:12:05Z' } }, 'Mira')
  assert.equal(`${ended?.lead}${ended?.tail}`, 'Call ended after 12 minutes.')
  assert.equal(callClock(3_723_000), '1:02:03')
  assert.ok(canCall({ state: 'apart', kind: 'long-distance', text: 'Long distance, Lisbon', outing: null, call: null }))
})

test('on a call their status line says so', () => {
  const status = { text: 'coffee first', set_by: 'app' as const, away: null, where: { state: 'call' as const, kind: 'call', text: 'On a call' } }
  assert.deepEqual(shown(status), { text: 'On a call', away: 'phone' })
  assert.deepEqual(shown({ ...status, where: { state: 'apart', kind: 'ringing', text: 'Calling you' } }), { text: 'Calling you', away: 'phone' })
})

test('a weekend visit across the distance says who is staying with whom, and until when', async () => {
  const { canCall, notTexting } = await import('../../src/features/conversation/whereText.ts')
  const visit = { id: 't1', direction: 'to-you' as const, city_name: 'Baltimore', start_date: '2026-10-17', end_date: '2026-10-18', leave_at: '16:00' }
  const staying: WhereState = { state: 'together', kind: 'staying', text: 'Staying with you until Sunday', outing: null, call: null, visit }
  const line = stripLine(staying, 'Mira')
  assert.equal(line?.lead, 'Mira is staying with you')
  assert.match(line?.tail ?? '', /^ until Sun/)
  assert.equal(stripAction(staying), null)
  assert.ok(notTexting(staying) && !canCall(staying))
  const hosting: WhereState = { ...staying, kind: 'hosting', visit: { ...visit, direction: 'host', city_name: 'Chicago' } }
  assert.equal(stripLine(hosting, 'Mira')?.lead, 'Staying with Mira in Chicago')
})

test('living together, the strip says home together or out, with the way to switch', () => {
  const home: WhereState = { state: 'together', kind: 'home', text: 'Home together', outing: null, home: { status: 'home' } }
  assert.deepEqual(homeLine(home, 'Mira'), { lead: 'Home together with Mira', action: 'out', label: 'Heading out' })
  assert.deepEqual(homeLine({ ...home, state: 'apart', kind: 'apart', home: { status: 'out' } }, 'Mira'),
    { lead: "You're out. Mira's at home.", action: 'home', label: "I'm home" })
  assert.equal(homeLine({ ...home, state: 'apart', kind: 'apart', home: { status: 'out', they_home: false } }, 'Mira')?.lead,
    "You're out.")  // They are at work or out themselves: the strip doesn't say they're home.
  assert.equal(homeLine({ ...home, home: null }, 'Mira'), null)
  assert.ok(inPerson(home))
})

test('Stay longer shows on the strip only while under way with a free hour after', () => {
  const base = { state: 'together', kind: 'out', text: '' } as const
  const outing = { state: 'now', longer_ok: true } as unknown as WhereOuting
  assert.equal(canStayLonger({ ...base, outing }), true)
  assert.equal(canStayLonger({ ...base, outing: { ...outing, longer_ok: false } }), false)
  assert.equal(canStayLonger({ ...base, outing: { ...outing, state: 'done' } }), false)
  assert.equal(canStayLonger(undefined), false)
})

test('on the way home after a meetup, with the time kept to its words', () => {
  const line = stripLine({ state: 'apart', kind: 'heading-home', text: 'On the subway home', outing: null, heading: { outing_id: 'o', place: 'Park', by: 'subway', words: 'on the subway home', back: '17:10' } }, 'Sett')
  assert.equal(line?.lead, 'Sett is on the subway home')
  assert.match(line?.tail ?? '', /^, back\u00a0around\u00a05:10\u00a0PM$/)
})

test('moving on to a second place: the strip names it, and Undo replaces Stay longer just after', () => {
  const next = { place: { ...outing.place, id: 'the-owl-bar', name: 'The Owl Bar', kind: 'bar' }, activity: 'drinks', at: '21:00', asked: false }
  const soon: WhereState = { ...out, outing: { ...outing, next, longer_ok: true } }
  const line = stripLine(soon, 'Mira')
  assert.equal(line?.place?.name, 'Ouzo Bay')
  assert.match(line?.tail ?? '', /^ until 9:00.*, then $/)
  assert.deepEqual(line?.then, { id: 'the-owl-bar', name: 'The Owl Bar' })
  assert.ok(canStayLonger(soon) && !canGoBack(soon))
  const moved: WhereState = { ...out, outing: { ...outing, place: next.place, longer_ok: true, undo_move: true } }
  assert.equal(stripLine(moved, 'Mira')?.then, null)
  assert.ok(canGoBack(moved) && !canStayLonger(moved))
})

test('the chat took them somewhere: the strip follows, and Back to replaces Stay longer for a minute or two', () => {
  const bus: WhereState = { ...out, text: 'On the bus', outing: { ...outing, longer_ok: true, place: { ...outing.place, id: '~scene', name: 'on the bus', kind: 'scene', label: 'on the bus' }, scene: { back: true, to: 'Ouzo Bay', kind: 'transit' } } }
  const line = stripLine(bus, 'Mira')
  assert.equal(line?.lead, 'On the bus')
  assert.equal(line?.place, null)
  assert.equal(line?.tail, '')  // No "until" while on the move.
  assert.ok(line?.clip)
  assert.ok(canBeBackAt(bus) && !canStayLonger(bus) && !canGoBack(bus))
  const later: WhereState = { ...bus, outing: { ...bus.outing!, scene: { back: false, to: 'Ouzo Bay', kind: 'transit' } } }
  assert.ok(!canBeBackAt(later) && canStayLonger(later))
  const walked: WhereState = { ...out, outing: { ...outing, place: { ...outing.place, id: 'harbor-promenade', name: 'Harbor East waterfront promenade', kind: 'landmark' }, scene: { back: true, to: 'Ouzo Bay', kind: 'place' } } }
  assert.equal(stripLine(walked, 'Mira')?.place?.name, 'Harbor East waterfront promenade')
})

test('somewhere again, the strip says until when; and first names only', () => {
  const walked: WhereState = { ...out, outing: { ...outing, scene: { back: false, to: 'Ouzo Bay', kind: 'place' } } }
  assert.match(stripLine(walked, 'Mira')?.tail ?? '', /^ until 9:00/)
  assert.equal(stripLine(yours, 'Dana Reyes')?.lead, 'Dana is at your place')
})
