import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import { BLANK, cardHeading, cardLabel, humanTerms, interestText } from '../../src/features/dating/datingText.ts'
import { undoLabel, answeredText, arrowWay, decide, hintText, missedText, nextHeard, pose, stamp, threshold, tilt, undoShown } from '../../src/features/dating/swipe.ts'

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

test('a held arrow key answers once, not the whole deck', () => {
  assert.equal(arrowWay('ArrowRight', { tagName: 'BODY' }, false), 'like')
  assert.equal(arrowWay('ArrowRight', { tagName: 'BODY' }, true), null)
  assert.equal(arrowWay('ArrowLeft', { tagName: 'BUTTON' }, true), null)
})

test('the hint names the arrow keys on a computer and the buttons on a phone', () => {
  assert.equal(hintText(3, false, true), '3 more after this one. Drag the card, or use the arrow keys.')
  assert.equal(hintText(0, true, true), 'The last one for now. Swipe the card, or use the buttons.')
  assert.equal(hintText(5, false, false), '5 more after this one.')
})

test('a screen reader hears the answer and who is next', () => {
  assert.equal(answeredText('Ashanti', 'like', 'Rachel, 40'), 'Liked Ashanti. Next: Rachel, 40.')
  assert.equal(answeredText('Ashanti', 'pass', null), 'Passed on Ashanti.')
  assert.equal(answeredText('Ashanti', 'like', null, 'No match with Ashanti this time.'), 'Liked Ashanti. No match with Ashanti this time.')
})

test('a like that was not returned says so, in the words of the era', () => {
  assert.equal(missedText('No match with {name} this time.', 'Ashanti'), 'No match with Ashanti this time.')
  assert.equal(missedText('{name} declined the introduction.', 'Edric'), 'Edric declined the introduction.')
  assert.equal(missedText('Your last letter went unanswered.', 'the notice'), 'Your last letter went unanswered.')
})

test('a card flies off the way it was answered, and only fades when motion is reduced', () => {
  assert.deepEqual(pose(0, 'like', false, 300), { x: 450, rotate: 14, opacity: 0, like: 1, pass: 0, lift: 1 })
  assert.deepEqual(pose(0, 'pass', true, 300), { x: 0, rotate: 0, opacity: 0, like: 0, pass: 1, lift: 1 })
  assert.equal(pose(50, null, true, 300).rotate, 0)
  assert.equal(pose(50, null, false, 300).x, 50)
})

test('Undo names who it brings back for a screen reader', () => {
  assert.equal(undoLabel('Ashanti', 'like'), 'Undo liking Ashanti')
  assert.equal(undoLabel('Rachel', 'pass'), 'Undo passing on Rachel')
})

test('a personal-column notice is never named, not even as the next one', () => {
  assert.equal(nextHeard('column', 'Gertrude, 34'), 'another notice')
  assert.equal(nextHeard('app', 'Rachel, 40'), 'Rachel, 40')
  assert.equal(nextHeard('matchmaker', 'Euron, 37'), 'Euron, 37')
  assert.equal(nextHeard('column', null), null)
})

test('Undo shows only for the answer the app can still take back, and not while the next one saves', () => {
  assert.equal(undoShown('town:a', 'town:a', false), true)
  assert.equal(undoShown('town:a', 'town:a', true), false)
  assert.equal(undoShown('town:a', null, false), false)  // Passed people back, an unmatch or another city.
  assert.equal(undoShown('town:a', 'town:b', false), false)
  assert.equal(undoShown(null, null, false), false)
})

test('Pass and Like keep keyboard focus while the card flies, so it can move to the next card', () => {
  const deck = readFileSync(new URL('../../src/features/dating/Deck.tsx', import.meta.url), 'utf8')
  assert.doesNotMatch(deck, /disabled=\{busy\}/)
  assert.match(deck, /aria-disabled=\{busy \|\| undefined\}/)
})

test('the Like stamp sits on the edge that stays on screen, and a notice wraps its actions under the text', () => {
  const css = readFileSync(new URL('../../src/styles.css', import.meta.url), 'utf8')
  assert.match(css, /\.dating-stamp\.like \{ left: 20px;/)
  assert.match(css, /\.notice \{ display: flex; flex-wrap: wrap;/)
  assert.match(css, /\.notice > span \{ flex: 1 1 14rem;/)
})

test('the interest line names one age once when the range is a single year', () => {
  assert.match(interestText({ ...BLANK, age_min: 22, age_max: 22 }), /aged 22, looking/)
  assert.match(interestText({ ...BLANK, age_min: 22, age_max: 30 }), /aged 22 to 30, looking/)
})

test('a card of a long-lived kind gives their age in human terms beside the real one', () => {
  const elf = { name: 'Aerwen', age: 225, life_age: 40 }
  assert.equal(cardHeading(elf), 'Aerwen, 225')
  assert.equal(humanTerms(elf), 'about 40 in human terms')
  assert.equal(cardLabel(elf), 'Aerwen, 225, about 40 in human terms')
  for (const human of [{ name: 'Maya', age: 29, life_age: null }, { name: 'Maya', age: 29 }, { name: 'Maya', age: 29, life_age: 29 }]) {
    assert.equal(humanTerms(human), '')
    assert.equal(cardLabel(human), 'Maya, 29')
  }
})
