import assert from 'node:assert/strict'
import { test } from 'node:test'
import { meterText, projectChange, projectField, timeOffText, yearOn } from '../../src/features/character/workText.ts'

test('time off reads as a sentence, a run of days as one stretch', () => {
  assert.equal(timeOffText([]), 'No time off booked.')
  assert.match(timeOffText(['2026-11-13']), /^1 vacation day coming up: .*13\.$/)
  assert.match(timeOffText(['2026-11-06', '2026-12-04', '2026-12-11']), /^Vacation days coming up: .*6, .*4 and .*11\.$/)
  assert.match(timeOffText(['2026-11-27', '2026-11-23', '2026-11-24', '2026-11-25', '2026-11-26']), /^Vacation .*23 to .*27 \(5 days\)\.$/)
  assert.ok(!/[A-Z][a-z]{2} \d/.test(timeOffText(['2026-12-11'])), 'a date never splits between month and day')
})

test('the numbers behind work read as words', () => {
  assert.equal(meterText({ vacation_total: 11, vacation_used: 2, pay_percent: 103 }), 'Vacation: 2 of 11 days used this year. Pay: 3% above where they started.')
  assert.equal(meterText({ vacation_total: 0, vacation_used: 0, pay_percent: 100 }), 'No paid vacation where they live. Pay: the same as where they started.')
})


test('a student has days with no classes, not vacation', () => {
  assert.equal(timeOffText([], true), 'No days off coming up.')
  assert.match(timeOffText(['2026-11-13'], true), /^No classes on .*13\.$/)
  assert.match(timeOffText(['2026-11-23', '2026-11-24', '2026-11-25'], true), /^A break .* \(3 days\)\.$/)
})

test('what they are working on shows without its article', () => {
  assert.equal(projectField('the reading list for upper-level photography'), 'Reading list for upper-level photography')
  assert.equal(projectField('a final portfolio review in photography'), 'Final portfolio review in photography')
})

test('the project form sends only what changed, and a due date moves up to a year on', () => {
  const view = { project: { title: "a wedding order for the miller's daughter", due: '2026-11-19' } }
  assert.deepEqual(projectChange(view, "Wedding order for the miller's daughter", '2026-11-19'), {})
  assert.deepEqual(projectChange(view, "Wedding order for the miller's daughter", '2026-11-26'), { due: '2026-11-26' })
  assert.deepEqual(projectChange(view, ' A new sign for the inn ', '2026-11-19'), { title: 'A new sign for the inn' })
  assert.equal(yearOn('2026-10-29'), '2027-10-29')
  assert.equal(yearOn('2027-03-01'), '2028-02-29')
})
