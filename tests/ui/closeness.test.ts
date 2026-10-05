import assert from 'node:assert/strict'
import { test } from 'node:test'
import { basisText, milestoneText, stageText } from '../../src/features/memories/closenessText.ts'
import type { Closeness } from '../../src/types.ts'

const stages = ['Just met', 'Getting to know each other', 'Friends', 'Close friends', 'Like old friends']
const base: Closeness = {
  level: 3, name: 'Friends', grown_level: 3, held_level: null, relationship: 'friendship', stages,
  days_talked: 5, shared_moments: 6, counted_moments: 5, first_day: '2026-10-01', counted_from: null,
  nickname: '', history: [], jokes: [], joke_candidates: [],
}

test('the basis names days and moments, and says when moments were capped', () => {
  assert.equal(basisText(base), 'You have talked on 5 days, with 6 shared moments in Memories (5 counted, never more than the days you talked).')
  assert.equal(basisText({ ...base, days_talked: 1, shared_moments: 1, counted_moments: 1 }), 'You have talked on 1 day, with 1 shared moment in Memories.')
  assert.equal(basisText({ ...base, days_talked: 0, counted_from: '2026-10-05' }), 'Counting restarted when you reset it. Nothing is counted yet.')
})

test('a hold says what shared history alone would give', () => {
  assert.equal(stageText(base, 'Mira'), 'Friends, from your shared history.')
  const held = { ...base, level: 5, name: 'Like old friends', held_level: 5 }
  assert.equal(stageText(held, 'Mira'), 'You are holding Mira at Like old friends. From shared history alone it would be Friends.')
})

test('a milestone says when and why', () => {
  assert.match(milestoneText({ level: 2, on: '2026-10-03', days: 3, moments: 0 }, stages), /^Getting to know each other on .*2026, after 3 days talking and 0 shared moments\.$/)
})
