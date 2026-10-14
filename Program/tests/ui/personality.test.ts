import assert from 'node:assert/strict'
import { test } from 'node:test'
import type { PersonalitySliders, PersonalityTrait } from '../../src/types.ts'
import { TYPES, chipsOf, moved, released, sameSliders, sourceLabel, stillShown, typeOf } from '../../src/features/character/personalityText.ts'

const TRAITS: PersonalityTrait[] = [
  { key: 'social', name: 'How social', low: 'Reserved', high: 'Outgoing', shows: ['a', 'b', 'c'] },
  { key: 'warmth', name: 'How they come across', low: 'Blunt', high: 'Warm', shows: ['a', 'b', 'c'] },
  { key: 'order', name: 'How they run their life', low: 'Goes with the flow', high: 'Organized', shows: ['a', 'b', 'c'] },
  { key: 'curiosity', name: 'How curious', low: 'Sticks to what they know', high: 'Tries anything', shows: ['a', 'b', 'c'] },
  { key: 'stress', name: 'How they handle stress', low: 'Steady', high: 'Feels everything', shows: ['a', 'b', 'c'] },
]
const rolled = (level: 0 | 1 | 2) => ({ level, source: 'rolled' as const })

test('the summary names every slider away from the middle in plain words', () => {
  const sliders: PersonalitySliders = { social: rolled(2), warmth: rolled(1), order: rolled(0), curiosity: rolled(1), stress: rolled(1) }
  assert.deepEqual(chipsOf(TRAITS, sliders), ['Outgoing', 'Goes with the flow'])
  assert.deepEqual(chipsOf(TRAITS, {}), ['Even-keeled all round'])
})

test('a type shows only when its four sliders are all off the middle, and every code is offered', () => {
  assert.equal(TYPES.length, 16)
  assert.equal(typeOf({ social: rolled(2), curiosity: rolled(2), warmth: rolled(2), order: rolled(2), stress: rolled(1) }), 'ENFJ')
  assert.equal(typeOf({ social: rolled(0), curiosity: rolled(0), warmth: rolled(0), order: rolled(0) }), 'ISTP')
  assert.equal(typeOf({ social: rolled(1), curiosity: rolled(2), warmth: rolled(2), order: rolled(2) }), null)
})

test('moving a slider makes it the user\'s; handing it back leaves it to the roll', () => {
  const sliders: PersonalitySliders = { social: rolled(2) }
  assert.deepEqual(moved(sliders, 'social', 0).social, { level: 0, source: 'you' })
  assert.equal(released(moved(sliders, 'social', 0), 'social').social, undefined)
  assert.equal(sourceLabel('you'), 'Set by you')
  assert.equal(sourceLabel('idea'), 'From your idea')
  assert.equal(sourceLabel('rolled'), 'Rolled')
  assert.ok(sameSliders(sliders, { social: rolled(2) }))
  assert.ok(!sameSliders(sliders, moved(sliders, 'social', 2)))
})

test('while a moved slider is checked the form keeps the answer it had, so the panel stays and keeps focus', () => {
  const shown = { sliders: { social: rolled(2) }, chips: ['Outgoing'], type: null }
  assert.equal(stillShown(shown), shown)
  assert.equal(stillShown(undefined), undefined)
})
