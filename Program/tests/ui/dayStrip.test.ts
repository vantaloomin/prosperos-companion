import assert from 'node:assert/strict'
import { test } from 'node:test'
import { clearOfNow, daySegments, labelFits, localParts } from '../../src/features/today/dayStrip.ts'

const slot = (starts_at: string, ends_at: string, label: string, kind = 'free') => ({ starts_at, ends_at, block: { label, kind } })

test('the day strip places their routine on their own day, cut at midnight', () => {
  // Lisbon is UTC+1 on 6 October 2026: their day runs 5 Oct 23:00 to 6 Oct 23:00 UTC.
  const slots = [slot('2026-10-05T22:00:00Z', '2026-10-06T06:00:00Z', 'Asleep', 'sleep'), slot('2026-10-06T08:00:00Z', '2026-10-06T16:00:00Z', 'At work', 'work'),
    slot('2026-10-06T22:00:00Z', '2026-10-07T06:00:00Z', 'Asleep', 'sleep')]
  const { segments, now } = daySegments(slots, '2026-10-06T11:00:00Z', 'Europe/Lisbon')
  assert.deepEqual(segments.map((segment) => [segment.label, Math.round(segment.left), Math.round(segment.width)]), [['Asleep', 0, 29], ['At work', 38, 33], ['Asleep', 96, 4]])
  assert.equal(Math.round(now), 50)
  assert.deepEqual(localParts('2026-10-06T11:00:00Z', 'Europe/Lisbon'), { date: '2026-10-06', minutes: 720 })
})

test('a part of the strip shows its name only where the whole word fits', () => {
  assert.equal(labelFits({ label: 'Afternoon', width: 25 }, 720), true)
  assert.equal(labelFits({ label: 'Afternoon', width: 16 }, 320), false)
  assert.equal(labelFits({ label: 'Asleep', width: 30 }, 320), true)
  assert.equal(labelFits({ label: 'Asleep', width: 30 }, 0), false)
})

test('a name in the strip is hidden where the now line would cross it', () => {
  assert.equal(clearOfNow({ label: 'Asleep', left: 0 }, 600, 3), false)
  assert.equal(clearOfNow({ label: 'Asleep', left: 0 }, 600, 50), true)
  assert.equal(clearOfNow({ label: 'Asleep', left: 10 }, 600, 5), true)
})
