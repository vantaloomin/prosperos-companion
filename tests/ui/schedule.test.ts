import assert from 'node:assert/strict'
import { test } from 'node:test'
import { cleanSchedule, newBlock, scheduleProblems, starterSchedule, toggleDay } from '../../src/features/character/schedule.ts'

test('days toggle on and off in weekday order', () => {
  assert.deepEqual(toggleDay([0, 4], 2), [0, 2, 4])
  assert.deepEqual(toggleDay([0, 2, 4], 2), [0, 4])
})

test('problems are named before saving', () => {
  const blocks = [{ ...newBlock(), label: '' }, { ...newBlock(), label: 'Gym', start: '10:00', end: '10:00', days: [] }]
  assert.deepEqual(scheduleProblems(blocks), ['Block 1 needs a name.', 'Gym starts and ends at the same time.', 'Gym needs at least one day.'])
  assert.deepEqual(scheduleProblems(starterSchedule()), [])
})

test('saved blocks are trimmed and blank themes dropped', () => {
  assert.deepEqual(cleanSchedule([{ ...newBlock(), label: ' Shift ', themes: ['regulars ', ' '] }])[0], { ...newBlock(), label: 'Shift', themes: ['regulars'] })
})
