import assert from 'node:assert/strict'
import { test } from 'node:test'
import { basisText, milestoneText, stageText } from '../../src/features/memories/closenessText.ts'
import type { Closeness } from '../../src/types.ts'

const stages = ['Just met', 'Getting to know each other', 'Friends', 'Close friends', 'Like old friends']
const base: Closeness = {
  level: 3, name: 'Friends', grown_level: 3, held_level: null, relationship: 'friendship', stages,
  days_talked: 5, shared_moments: 6, counted_moments: 5, first_day: '2026-10-01', counted_from: null,
  nickname: '', history: [], jokes: [], joke_candidates: [], earned_level: 3, ceiling_level: null, starting_level: 1,
  cooling: false, cooled_steps: 0, warm_days_left: 0, silent_days: 0, set_on: null,
}

test('the basis names days and moments, and says when moments were capped', () => {
  assert.equal(basisText(base), 'You have talked on 5 days, with 6 shared moments in Memories (5 counted, never more than the days you talked).')
  assert.equal(basisText({ ...base, days_talked: 1, shared_moments: 1, counted_moments: 1 }), 'You have talked on 1 day, with 1 shared moment in Memories.')
  assert.equal(basisText({ ...base, days_talked: 0, counted_from: '2026-10-05' }), 'Counting restarted when you reset it. Nothing is counted yet.')
})

test('a hold says what shared history alone would give', () => {
  assert.equal(stageText(base, 'Mira'), 'Friends, from your shared history.')
  const held = { ...base, level: 5, name: 'Like old friends', held_level: 5 }
  assert.equal(stageText(held, 'Mira'), 'You are keeping Mira at Like old friends. Without that it would be Friends.')
})

test('a set stage, a start, a ceiling and cooling each explain themselves', () => {
  assert.match(stageText({ ...base, set_on: '2026-10-08' }, 'Mira'), /^Friends\. You set it on .*2026 and it grows from there\.$/)
  assert.equal(stageText({ ...base, starting_level: 3 }, 'Mira'), 'Friends. You started at Friends and it grows from there.')
  assert.equal(stageText({ ...base, earned_level: 4, ceiling_level: 3 }, 'Mira'), 'Friends, the closest you let it get. From your shared history alone it would be Close friends.')
  const cooled = { ...base, level: 2, name: 'Getting to know each other', grown_level: 2, cooling: true, cooled_steps: 1, warm_days_left: 1 }
  assert.equal(stageText(cooled, 'Mira'), 'Getting to know each other: it has cooled a step from Friends after a long time apart. Talking on 1 more day brings a step back.')
})

test('a milestone says when and why', () => {
  assert.equal(milestoneText({ kind: 'start', level: 3, on: null }, stages), 'Started at Friends.')
  assert.match(milestoneText({ kind: 'set', level: 4, on: '2026-10-08' }, stages), /^You set it to Close friends on .*2026\.$/)
  assert.match(milestoneText({ level: 2, on: '2026-10-03', days: 3, moments: 0 }, stages), /^Getting to know each other on .*2026, after 3 days talking and 0 shared moments\.$/)
})
