import assert from 'node:assert/strict'
import test from 'node:test'
import { breakupLine, breakupStrip, mendLabel, type BreakupView } from '../../src/features/character/breakupText.ts'

const base: BreakupView = { stage: 'strained', text: 'Things are strained', since: '2026-10-12', by: null, id: 'b', odds: [], strip: true, mendable: false, ladder: 'romance', on: true }

test('the warnings come first, in plain words', () => {
  assert.equal(breakupLine(base, 'Mira Costa'), 'Things are strained')
  assert.equal(breakupLine({ ...base, stage: 'thinking', text: "They're thinking about a break" }, 'Mira'), "They're thinking about a break")
  assert.equal(breakupStrip(base, 'Mira Costa'), 'Things are strained with Mira')
  assert.equal(breakupStrip({ ...base, stage: 'thinking' }, 'Mira'), 'Mira is thinking about a break')
})

test('a break and a breakup say when and who', () => {
  assert.match(breakupLine({ ...base, stage: 'break', text: 'On a break', by: 'them' }, 'Mira'), /^On a break since .+ · Mira asked for it$/)
  assert.match(breakupLine({ ...base, stage: 'ended', text: 'Broke up', by: 'you' }, 'Mira'), /^Broke up .+ · you ended it$/)
  assert.equal(breakupStrip({ ...base, stage: 'ended', ladder: 'friendship' }, 'Mira'), 'You and Mira fell out')
  assert.equal(breakupStrip({ ...base, stage: 'ended', strip: false }, 'Mira'), '')
  assert.equal(mendLabel({ ...base, stage: 'ended' }), 'Get back together')
  assert.equal(mendLabel(base), 'Patch things up')
  assert.equal(breakupLine(undefined, 'Mira'), '')
})
