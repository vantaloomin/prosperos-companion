import assert from 'node:assert/strict'
import { test } from 'node:test'
import { shiftToFit } from '../../src/components/fitOnScreen.ts'

test('a pop-over that fits stays where it is', () => {
  assert.equal(shiftToFit(20, 300, 390), 0)
})

test('a pop-over running off the right edge of a phone moves back in', () => {
  assert.equal(shiftToFit(215, 508, 390), -126)
})

test('a pop-over running off the left edge moves back in', () => {
  assert.equal(shiftToFit(-30, 200, 390), 38)
})

test('a pop-over wider than the window keeps its start on screen', () => {
  assert.equal(shiftToFit(100, 600, 390), -92)
})
