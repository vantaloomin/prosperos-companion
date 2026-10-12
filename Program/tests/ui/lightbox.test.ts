import assert from 'node:assert/strict'
import { test } from 'node:test'
import { saveName, stepTo, swipeAction } from '../../src/components/lightboxState.ts'

test('stepping stays on the first and last picture rather than wrapping round', () => {
  assert.equal(stepTo(0, -1, 3), 0)
  assert.equal(stepTo(1, 1, 3), 2)
  assert.equal(stepTo(2, 1, 3), 2)
  assert.equal(stepTo(0, 1, 1), 0)
})

test('a sideways swipe moves between pictures and a drag down closes', () => {
  assert.equal(swipeAction(-120, 10), 'next')
  assert.equal(swipeAction(120, -20), 'previous')
  assert.equal(swipeAction(10, 140), 'close')
  assert.equal(swipeAction(20, 30), null)
  assert.equal(swipeAction(-20, -140), null)
})

test('a saved picture is named for who sent it and when', () => {
  const when = new Date(2026, 9, 5, 12, 0).toISOString()
  assert.equal(saveName({ from: 'Mira', when }), 'Mira 2026-10-05 12-00')
  assert.equal(saveName({ from: 'You', when: 'not a date' }), 'You')
  assert.equal(saveName({ from: 'A/B: "C"', when }), 'A B C 2026-10-05 12-00')
})
