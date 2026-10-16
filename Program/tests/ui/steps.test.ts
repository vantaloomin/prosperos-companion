import assert from 'node:assert/strict'
import test from 'node:test'
import { PACE_LEVELS, askText, howText, plannedText, stepDate } from '../../src/features/character/stepsText.ts'

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
