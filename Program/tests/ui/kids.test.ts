import assert from 'node:assert/strict'
import { test } from 'node:test'
import { kidLine, kidsHint, stepParentLine, whereHint } from '../../src/features/character/familyText.ts'
import type { Kid, KidsView } from '../../src/types.ts'

const kid = (changes: Partial<Kid>): Kid => ({
  id: 'k1', name: 'Leo', pronouns: 'he/him', born_on: '2019-05-01', age: 7, age_text: '7', relation: 'son', ...changes,
})
const view = (changes: Partial<KidsView>): KidsView => ({
  shown: true, how: 'description', kids: [kid({})], other: { name: 'Mark', role: 'ex-husband' }, pattern: 'with_them',
  pattern_how: 'fixed', patterns: [], step_parent: false, ...changes,
})

test('one of their kids reads as name, age and son or daughter', () => {
  assert.equal(kidLine(kid({})), 'Leo, 7, son')
  assert.equal(kidLine(kid({ name: 'Ivy', age_text: 'a newborn', relation: 'daughter' })), 'Ivy, newborn, daughter')
  assert.equal(kidLine(kid({ age_text: '7 months old' })), 'Leo, 7 months old, son')
})

test('the hints say where the kids came from and who decided where they live', () => {
  assert.equal(kidsHint(view({}), 'Dana Reyes'), "Read from Dana's description. Take a child out of their life if they shouldn't be there.")
  assert.match(kidsHint(view({ how: 'town' }), 'Dana'), /while living in town/)
  assert.match(kidsHint(view({ how: 'seeded' }), 'Dana'), /^Picked by the app for Dana\./)
  assert.equal(whereHint(view({}), 'Dana'), "Read from Dana's description. Mark, their other parent, is in Dana's circle as their ex-husband.")
  assert.equal(whereHint(view({ pattern_how: 'set', other: null }), 'Dana'), 'You set this.')
})

test('living with a romance companion makes you their step-parent', () => {
  assert.equal(stepParentLine(view({}), 'Dana'), null)
  assert.equal(stepParentLine(view({ step_parent: true }), 'Dana'), "You live with Dana, so you're Leo's step-parent.")
  assert.equal(stepParentLine(view({ step_parent: true, kids: [kid({}), kid({ name: 'Mia' })] }), 'Dana'), "You live with Dana, so you're their step-parent.")
})
