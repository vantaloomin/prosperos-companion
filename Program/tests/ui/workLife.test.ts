import assert from 'node:assert/strict'
import { test } from 'node:test'
import { meterText, timeOffText } from '../../src/features/character/workText.ts'

test('time off reads as a sentence, a run of days as one stretch', () => {
  assert.equal(timeOffText([]), 'No time off booked.')
  assert.match(timeOffText(['2026-11-13']), /^1 vacation day coming up: .*13\.$/)
  assert.match(timeOffText(['2026-11-06', '2026-12-04', '2026-12-11']), /^Vacation days coming up: .*6, .*4 and .*11\.$/)
  assert.match(timeOffText(['2026-11-27', '2026-11-23', '2026-11-24', '2026-11-25', '2026-11-26']), /^Vacation .*23 to .*27 \(5 days\)\.$/)
})

test('the numbers behind work read as words', () => {
  assert.equal(meterText({ vacation_total: 11, vacation_used: 2, pay_percent: 103 }), 'Vacation: 2 of 11 days used this year. Pay: 3% above where they started.')
  assert.equal(meterText({ vacation_total: 0, vacation_used: 0, pay_percent: 100 }), 'No paid vacation where they live. Pay: the same as where they started.')
})

