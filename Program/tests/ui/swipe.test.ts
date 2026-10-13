import assert from 'node:assert/strict'
import { test } from 'node:test'
import { answeredText, arrowWay, decide, hintText, pose, stamp, threshold, tilt } from '../../src/features/dating/swipe.ts'

test('a drag past a third of the card likes to the right and passes to the left', () => {
  assert.equal(threshold(360), 120)
  assert.equal(threshold(150), 80)
  assert.equal(decide(130, 0, 360), 'like')
  assert.equal(decide(-130, 0, 360), 'pass')
})

test('a short slow drag springs back, and a quick flick counts', () => {
  assert.equal(decide(60, 0.1, 360), null)
  assert.equal(decide(10, 2, 360), null)
  assert.equal(decide(40, 1, 360), 'like')
  assert.equal(decide(-40, -1, 360), 'pass')
  assert.equal(decide(60, -1, 360), null)
})

test('the card leans with the drag, never past the limit, and the stamp fills by the threshold', () => {
  assert.equal(tilt(0, 360), 0)
  assert.ok(tilt(60, 360) > 0 && tilt(-60, 360) < 0)
  assert.equal(tilt(5000, 360), 14)
  assert.deepEqual(stamp(20, 360), { like: 0, pass: 0 })
  assert.deepEqual(stamp(72, 360), { like: 1, pass: 0 })
  assert.deepEqual(stamp(-48, 360), { like: 0, pass: 0.5 })
  assert.deepEqual(stamp(-500, 360), { like: 0, pass: 1 })
  assert.deepEqual(stamp(0, 360), { like: 0, pass: 0 })
})

test('arrow keys answer, except while typing or choosing', () => {
  assert.equal(arrowWay('ArrowRight', { tagName: 'BODY' }), 'like')
  assert.equal(arrowWay('ArrowLeft', { tagName: 'BUTTON' }), 'pass')
  assert.equal(arrowWay('ArrowUp', { tagName: 'BODY' }), null)
  assert.equal(arrowWay('ArrowLeft', { tagName: 'SELECT' }), null)
  assert.equal(arrowWay('ArrowRight', { tagName: 'TEXTAREA' }), null)
  assert.equal(arrowWay('ArrowRight', { tagName: 'DIV', isContentEditable: true }), null)
  assert.equal(arrowWay('ArrowRight', null), 'like')
})

test('the hint names the arrow keys on a computer and the buttons on a phone', () => {
  assert.equal(hintText(3, false, true), '3 more after this one. Drag the card, or use the arrow keys.')
  assert.equal(hintText(0, true, true), 'The last one for now. Swipe the card, or use the buttons.')
  assert.equal(hintText(5, false, false), '5 more after this one.')
})

test('a screen reader hears the answer and who is next', () => {
  assert.equal(answeredText('Ashanti', 'like', 'Rachel, 40'), 'Liked Ashanti. Next: Rachel, 40.')
  assert.equal(answeredText('Ashanti', 'pass', null), 'Passed on Ashanti.')
})

test('a card flies off the way it was answered, and only fades when motion is reduced', () => {
  assert.deepEqual(pose(0, 'like', false, 300), { x: 450, rotate: 14, opacity: 0, like: 1, pass: 0, lift: 1 })
  assert.deepEqual(pose(0, 'pass', true, 300), { x: 0, rotate: 0, opacity: 0, like: 0, pass: 1, lift: 1 })
  assert.equal(pose(50, null, true, 300).rotate, 0)
  assert.equal(pose(50, null, false, 300).x, 50)
})
