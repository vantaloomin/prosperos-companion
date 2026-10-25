import assert from 'node:assert/strict'
import { test } from 'node:test'
import { kidAgeChoice, kidChange, kidLine, kidSaved, kidsHint, madeUpLine, otherHint, parentChoice, removedLine, standingLine, whereHint, whereLabel, wherePick } from '../../src/features/character/familyText.ts'
import type { Kid, KidsView } from '../../src/types.ts'

const kid = (changes: Partial<Kid>): Kid => ({
  id: 'k1', name: 'Leo', pronouns: 'he/him', born_on: '2019-05-01', age: 7, age_text: '7', relation: 'son', ...changes,
})
const view = (changes: Partial<KidsView>): KidsView => ({
  shown: true, how: 'description', kids: [kid({})], other: { id: 'p1', name: 'Mark', role: 'ex-husband', made: true, made_up: false }, pattern: 'with_them',
  pattern_how: 'fixed', patterns: [], step_parent: false, ...changes,
})

test('one of their kids reads as name, age and son or daughter', () => {
  assert.equal(kidLine(kid({})), 'Leo, 7, son')
  assert.equal(kidLine(kid({ name: 'Ivy', age_text: 'a newborn', relation: 'daughter' })), 'Ivy, newborn, daughter')
  assert.equal(kidLine(kid({ age_text: '7 months old' })), 'Leo, 7 months old, son')
})

test('the hints say where the kids came from and who decided where they live', () => {
  assert.equal(kidsHint(view({}), 'Dana Reyes'), "Read from Dana's description. Edit a child, or take them out of their life if they shouldn't be there.")
  assert.equal(kidsHint(view({ kids: [kid({ by_hand: true })] }), 'Dana'), "You added them. Edit a child, or take them out of Dana's life.")
  assert.match(kidsHint(view({ how: 'town' }), 'Dana'), /while living in town/)
  assert.match(kidsHint(view({ how: 'seeded' }), 'Dana'), /^Picked by the app for Dana\./)
  assert.equal(whereHint(view({}), 'Dana'), "Read from Dana's description.")
  assert.equal(whereHint(view({ pattern_how: 'seeded', detail: "with Dana, every other weekend at Mark's" }), 'Dana'),
    "Picked by the app: with Dana, every other weekend at Mark's.")
  assert.equal(whereHint(view({ pattern_how: 'set', other: null }), 'Dana'), 'You set this.')
})

test('the first choice of where the kids live names the description or the app', () => {
  assert.equal(wherePick(view({}), 'Sam', 'Mostly with Sam'), "From Sam's description (Mostly with Sam)")
  assert.equal(wherePick(view({ pattern_how: 'seeded' }), 'Dana', 'Mostly with Dana'), 'Let the app decide (Mostly with Dana)')
  assert.equal(wherePick(view({ pattern_how: 'set' }), 'Dana', 'Half and half'), 'Let the app decide (what fits them)')
})

test('a romance shows where you stand with their kids', () => {
  assert.equal(standingLine(view({}), 'Dana'), null)
  assert.deepEqual(standingLine(view({ step_parent: true }), 'Dana'), { label: 'Step-parent', text: "you live with Dana, so you're Leo's step-parent." })
  assert.equal(standingLine(view({ step_parent: true, kids: [kid({ name: 'Major' }), kid({ name: 'Logan' })] }), 'Sam')?.text, "you live with Sam, so you're Major and Logan's step-parent.")
  assert.deepEqual(standingLine(view({ meeting: 'unmet' }), 'Dana Reyes'), { label: 'Not met yet', text: 'Dana will bring it up when the time feels right.' })
  assert.equal(standingLine(view({ meeting: 'met', kids: [kid({}), kid({ name: 'Mia' })] }), 'Dana')?.text, "you've met them.")
})

test('the other parent is named with who they are, and a made-up one says so', () => {
  assert.equal(otherHint(view({}), 'Dana'), "Mark is Dana's ex-husband.")
  assert.equal(otherHint(view({ other: { id: 'p2', name: 'Aaliyah Soren', role: 'co-parent', made: true, made_up: true } }), 'Sarek'),
    'Aaliyah is Sarek\'s co-parent. Picked by the app. Pick "Someone else" to name who it really is.')
  assert.equal(otherHint(view({ other: null }), 'Dana'), 'Dana is raising them on their own.')
  assert.equal(parentChoice({ id: 'p1', name: 'Mark', role: 'ex-husband', made: false, made_up: false }), 'Mark (ex-husband)')
})

test('the add and edit forms send only what was filled in or changed', () => {
  assert.deepEqual(kidChange(undefined, '  ', '', -1), {})
  assert.deepEqual(kidChange(undefined, 'Spock ', 'he/him', 5), { name: 'Spock', pronouns: 'he/him', age: 5 })
  assert.deepEqual(kidChange(kid({}), 'Leo', 'he/him', 7), {})
  assert.deepEqual(kidChange(kid({}), 'Spock', 'he/him', 5), { name: 'Spock', age: 5 })
  assert.equal(kidAgeChoice(-1), 'Let the app pick')
  assert.equal(kidAgeChoice(0), 'Under a year')
  assert.equal(kidSaved(undefined, view({ kids: [kid({}), kid({ name: 'Ivy', by_hand: true })] })), 'Added Ivy.')
})

test('the form and notice wording follows the review', () => {
  assert.equal(whereLabel(view({})), 'Where Leo lives')
  assert.equal(whereLabel(view({ kids: [kid({}), kid({ id: 'k2', name: 'Mia' })] })), 'Where the kids live')
  assert.equal(removedLine('Spock', 'Sarek Hale'), "Spock is out of Sarek's life.")
  assert.equal(madeUpLine('Edward Lin'), 'The app made up Edward. Edward becomes the person you name here.')
})
