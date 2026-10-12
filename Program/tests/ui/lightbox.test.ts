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

test('a saved picture is named for what it shows', () => {
  assert.equal(saveName('Photo from Mira: Mira painted by the river.'), 'photo-from-mira-mira-painted-by-the-river')
  assert.equal(saveName('!!!'), 'picture')
})
