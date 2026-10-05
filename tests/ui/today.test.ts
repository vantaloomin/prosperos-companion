import assert from 'node:assert/strict'
import { test } from 'node:test'
import { availabilityShort, availabilityText, moodText, pauseToFill } from '../../src/features/today/today.ts'

test('availability explains, without locking anything', () => {
  const today = { companion_timezone: 'UTC', availability: { state: 'asleep' as const, label: 'Asleep', until: '2026-10-06T06:00:00+00:00' } }
  assert.match(availabilityText(today, 'Mira'), /^Mira is asleep until .+ their time\. Replies may be slow\.$/)
  assert.equal(availabilityText({ companion_timezone: 'UTC', availability: { state: 'free', label: '', until: null } }, 'Mira'), 'Mira is free.')
})

test('the mood names its cause and the traits behind it', () => {
  const text = moodText({ id: 'm', kind: 'absence', intensity: 'moderate', away_hours: 72, traits: ['guilt over absence'], expires_at: '' }, 'Mira')
  assert.equal(text, 'Mira is in a moderate mood about the 3 days you were apart, from the traits you gave them (guilt over absence).')
})

test('only an ended pause that was not filled in is offered', () => {
  const pauses = [
    { id: 'a', started_at: '3', ended_at: null, catch_up_requested_at: null, catch_up_run_id: null },
    { id: 'b', started_at: '2', ended_at: '2.5', catch_up_requested_at: '2.6', catch_up_run_id: 'r' },
    { id: 'c', started_at: '1', ended_at: '1.5', catch_up_requested_at: null, catch_up_run_id: null },
  ]
  assert.equal(pauseToFill(pauses)?.id, 'c')
})

test('the header gets a few words', () => {
  assert.equal(availabilityShort({ state: 'working', label: 'Bakery shift', until: null }), 'Busy: bakery shift')
  assert.equal(availabilityShort({ state: 'asleep', label: 'Asleep', until: null }), 'Asleep')
})
