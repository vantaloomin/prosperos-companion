import assert from 'node:assert/strict'
import test from 'node:test'
import { PACE_LEVELS, askText, howText, movingText, newcomerText, plannedText, stepDate } from '../../src/features/character/stepsText.ts'

test('the Relationship pace slider has four steps', () => {
  assert.deepEqual(PACE_LEVELS.map((level) => level.label), ['Only when you bring it up', 'Slow', 'True to life', 'Fast'])
})

test('each step says who moved it there', () => {
  assert.equal(howText('them', 'Mira Costa'), 'Mira brought it up')
  assert.equal(howText('set', 'Mira'), 'you set it')
})

test('what came up lately says the answer', () => {
  const ask = { id: 'a', step: 'exclusive', side: 'them' as const, status: 'yes' as const, topic: 'being exclusive', on: '2026-10-05', consequence_id: null }
  assert.equal(askText(ask, 'Mira'), 'Mira brought up being exclusive. You said yes.')
  assert.equal(askText({ ...ask, side: 'you', status: 'not_yet', topic: 'a key to your place' }, 'Mira'), 'You brought up a key to their place. Mira said not yet.')
  assert.equal(askText({ ...ask, step: 'confession', status: 'no' }, 'Mira'), 'Mira told you how they feel. You said you would rather stay friends.')
})

test('the planned note names the step, with a short date that never breaks', () => {
  const planned = { step: 'their_people', due_on: '2026-10-28', consequence_id: null, topic: 'meeting your people' }
  assert.match(plannedText(planned, 'Mira Costa'), /^Mira plans to bring up meeting their people around .+\.$/)
  assert.equal(plannedText({ ...planned, step: 'confession', topic: 'how you feel' }, 'Mira').startsWith('Mira plans to tell you how they feel'), true)
  assert.equal(stepDate('2026-10-28').includes(' '), false)
})

test('moving in together says whose place, or who moves, and when', () => {
  const moving = { status: 'moving' as const, plan: 'yours' as const, city: 'Baltimore', place: 'Canton', home: '', move_on: '2026-10-28', moved_on: null, consequence_id: null }
  assert.equal(movingText(moving, 'Mira Costa'), `Mira is moving into your place on ${stepDate('2026-10-28')}.`)
  assert.equal(movingText({ ...moving, plan: 'new' }, 'Mira'), `Moving into a new place in Canton on ${stepDate('2026-10-28')}.`)
  assert.equal(movingText({ ...moving, plan: 'them' }, 'Mira'), `Mira is moving to Baltimore to live with you on ${stepDate('2026-10-28')}.`)
  assert.equal(movingText({ ...moving, status: 'waiting', plan: 'you', city: 'Chicago' }, 'Mira'), 'Mira asked you to move to Chicago to live together.')
  assert.equal(movingText({ ...moving, status: 'moved', moved_on: '2026-11-02', home: 'a two-bedroom in Canton' }, 'Mira'),
    `Since ${stepDate('2026-11-02')}, a two-bedroom in Canton.`)
})

test('sharing a home with another partner says who lives there, and why a move waits', () => {
  const base = { status: 'moving' as const, plan: 'yours' as const, city: 'Baltimore', place: 'Canton', home: '', move_on: '2026-11-01', moved_on: null, consequence_id: null }
  const joining = { ...base, joins: true, ready: true, with: ['Mira'], not_ready: [] }
  assert.equal(movingText(joining, 'Theo Park'), `Theo is moving in with you and Mira on ${stepDate('2026-11-01')}.`)
  assert.equal(movingText({ ...joining, status: 'waiting', move_on: null, not_ready: ['Mira'] }, 'Theo'),
    "Theo would like to move in with you and Mira. Waiting: Mira isn't ready to share your home yet.")
  assert.equal(movingText({ ...joining, status: 'waiting', move_on: null, ready: false }, 'Theo'),
    "Theo would like to live with you, but isn't ready to share a home with Mira yet.")
  assert.equal(movingText({ ...base, status: 'moved', moved_on: '2026-11-02', home: 'a one-bedroom in Canton', with: ['Theo'] }, 'Mira'),
    `Since ${stepDate('2026-11-02')}, a one-bedroom in Canton, with Theo.`)
  const newcomer = { name: 'Theo', status: 'waiting' as const, move_on: null, open: false, not_ready: ['Mira'], consequence_id: null }
  assert.equal(newcomerText(newcomer, 'Mira Solano'), "Theo would like to move in too. Mira isn't ready to share your home yet.")
  assert.equal(newcomerText({ ...newcomer, status: 'moving', move_on: '2026-11-01', open: true, not_ready: [] }, 'Mira'),
    `Theo is moving in too, on ${stepDate('2026-11-01')}.`)
})
