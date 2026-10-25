import assert from 'node:assert/strict'
import { test } from 'node:test'
import { clockGap, gapText, hoursHint, zoneOffset } from '../../src/features/character/theirHoursText.ts'

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
  const fit = { mode: 'fit' as const, shift: -540, why: 'remote', zone: '', fit: -540 }
  const hint = (mode: 'fit' | 'mine' | 'city', saved: 'fit' | 'mine' | 'city') => hoursHint({ hours: { ...fit, mode }, saved, city: 'Osaka', gap: 13 * 60 })
  assert.equal(hint('fit', 'fit'), "The app moved their week 9 hours earlier so they're free on your evenings; they work remotely on odd hours. Turn this on to put their whole day on your clock.")
  assert.match(hint('fit', 'mine'), /^Saving moves their week back to the fitted hours, 9 hours earlier/)
  assert.match(hint('fit', 'city'), /^Saving moves their week 9 hours earlier/)
  assert.equal(hint('city', 'city'), "Their day runs on Osaka's clock, 13 hours ahead of you. Turn this on to put their whole day on your clock.")
  assert.match(hint('city', 'fit'), /^Saving puts them back on Osaka's clock/)
  assert.match(hint('mine', 'fit'), /Saving moves their whole day onto your time\.$/)
  assert.doesNotMatch(hint('mine', 'mine'), /Saving/)
})
