import assert from 'node:assert/strict'
import test from 'node:test'
import { apartHint, breakupLine, breakupStrip, mendLabel, type BreakupView } from '../../src/features/character/breakupText.ts'

const base: BreakupView = { stage: 'strained', text: 'Things are strained', summary: '', since: '2026-10-12', by: null, id: 'b', odds: [], strip: true, mendable: false, ladder: 'romance', on: true }

test('the warnings come first, in plain words', () => {
  assert.deepEqual(breakupLine(base, 'Mira Costa'), { status: 'Things are strained', detail: '' })
  assert.equal(breakupLine({ ...base, stage: 'thinking', text: "They're thinking about a break" }, 'Mira').status, "They're thinking about a break")
  assert.equal(breakupStrip(base, 'Mira Costa'), 'Things are strained with Mira.')
  assert.equal(breakupStrip({ ...base, stage: 'thinking' }, 'Mira'), 'Mira is thinking about a break.')
})

test('a break and a breakup say when and who', () => {
  const onBreak = breakupLine({ ...base, stage: 'break', text: 'On a break', by: 'them' }, 'Mira')
  assert.match(onBreak.status, /^On a break since .+\.$/)
  assert.equal(onBreak.detail, 'Mira asked for it.')
  assert.equal(breakupLine({ ...base, stage: 'ended', text: 'Broke up', by: 'you' }, 'Mira').detail, 'You ended it.')
  assert.equal(breakupStrip({ ...base, stage: 'ended', ladder: 'friendship' }, 'Mira'), 'You and Mira fell out.')
  assert.equal(breakupStrip({ ...base, stage: 'ended', strip: false }, 'Mira'), '')
  assert.equal(mendLabel({ ...base, stage: 'ended' }), 'Get back together')
  assert.equal(mendLabel(base), 'Patch things up')
  assert.equal(breakupLine(undefined, 'Mira').status, '')
})

test('the steps hint says what getting back together means', () => {
  assert.equal(apartHint({ ...base, stage: 'ended' }), "Getting back together starts again from a key to each other's place.")
  assert.equal(apartHint({ ...base, stage: 'break' }), 'Patch things up to pick up where you left off.')
  assert.equal(apartHint({ ...base, stage: 'ended', ladder: 'friendship' }), 'Make up to pick up where you left off.')
})
