import assert from 'node:assert/strict'
import { test } from 'node:test'
import { FAMILY_SHAPES_LEVELS } from '../../src/features/character/familiesText.ts'
import { inFamily, longAgoFacts, longAgoText, outOfTouch, outOfTouchText } from '../../src/features/today/familyText.ts'
import type { CirclePerson } from '../../src/types.ts'

const person = (changes: Partial<CirclePerson>) => ({ id: 'a', name: 'Ruth', role: 'mom', status: 'active', ...changes }) as CirclePerson
const kin = { id: 'p1', ties: {} }

test('family in touch, out of touch and long gone fall in their own groups', () => {
  assert.equal(inFamily(person({ kin })), true)
  assert.equal(inFamily(person({})), false)
  assert.equal(inFamily(person({ kin, estranged: true, status: 'removed' })), false)
  assert.equal(outOfTouch(person({ kin, estranged: true, status: 'removed' })), true)
  assert.equal(inFamily(person({ kin, late: '2010-05-15', long_ago: 14 })), false)
  assert.equal(outOfTouch(person({ kin, late: '2010-05-15', long_ago: 14 })), false)
})

test('someone who died before now reads by the companion age then', () => {
  assert.equal(longAgoText('Mira', 14), 'Passed away when Mira was 14.')
  assert.equal(longAgoText('Mira', 1), 'Passed away when Mira was a baby.')
  assert.equal(longAgoText('Mira', 0), 'Passed away before Mira was born.')
})

test('the Family shapes slider has four steps', () => {
  assert.deepEqual(FAMILY_SHAPES_LEVELS.map((level) => level.label), ['Simple', 'Gentle', 'True to life', 'More drama'])
})

test('out of touch reads by first names, and a long-ago death by the age they died at', () => {
  assert.equal(outOfTouchText('Dana Price', 'Jessica Price'), "Dana and Jessica don't talk anymore. Restore to bring them back into each other's lives.")
  assert.equal(longAgoFacts(person({ role: 'dad', pronouns: 'he/him', age: 54, long_ago: 22 })), 'dad · he/him · died at 54')
  assert.ok(FAMILY_SHAPES_LEVELS.every((level) => level.hint.endsWith('Applies to companions made from now on.')))
})
