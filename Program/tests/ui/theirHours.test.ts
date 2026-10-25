import assert from 'node:assert/strict'
import { test } from 'node:test'
import { clockGap, fitText, gapText, mineHint, zoneOffset } from '../../src/features/character/theirHoursText.ts'

test('the gap between two clocks follows daylight saving', () => {
  const october = new Date('2026-10-05T12:00:00Z')
  assert.equal(zoneOffset('Asia/Tokyo', october), 9 * 60)
  assert.equal(zoneOffset('America/New_York', october), -4 * 60)
  assert.equal(clockGap('Asia/Tokyo', 'America/New_York', october), 13 * 60)
  assert.equal(clockGap('Asia/Tokyo', 'America/New_York', new Date('2026-12-05T12:00:00Z')), 14 * 60)
  assert.equal(zoneOffset('Not/AZone', october), 0)
})

test('the switch and the note say what moves in plain words', () => {
  assert.equal(gapText(13 * 60), '13 hours ahead of you')
  assert.equal(gapText(-60), '1 hour behind you')
  assert.equal(fitText({ mode: 'fit', shift: 240, why: 'night_owl', zone: '', fit: 240 }),
    'The app moved their week 4 hours later than written so they are free on your evenings, a night owl.')
  assert.match(mineHint('Osaka', 13 * 60, false, true), /Osaka's clock, 13 hours ahead of you/)
  assert.match(mineHint('Osaka', 13 * 60, true, false), /Saving moves their week\.$/)
  assert.doesNotMatch(mineHint('Osaka', 13 * 60, true, true), /Saving/)
})
