import assert from 'node:assert/strict'
import { test } from 'node:test'
import { anotherHint, arrivalText, careHint, ourChildLine, sheetText } from '../../src/features/character/familyText.ts'
import { FAMILY_LIFE_LEVELS } from '../../src/features/character/familiesText.ts'
import type { FamilyView, OurChild, OursView } from '../../src/types.ts'

const child = (changes: Partial<OurChild>): OurChild => ({
  id: 'c1', name: 'Mia', pronouns: 'she/her', born_on: '2028-03-03', arrived_on: '2028-03-03', journey_id: 'j1', age: 2,
  age_text: '2', grown: false, relation: 'daughter', temperament: 'easygoing and quick to laugh', likes: 'puddles',
  quirk: 'Mia names every bird Gerald.', milestones: [], latest: null, ...changes,
})
const day = (value: string) => value

test('a child of yours reads as name, age and who they are', () => {
  assert.equal(ourChildLine(child({})), 'Mia, 2 years old, daughter')
  assert.equal(ourChildLine(child({ age_text: 'a newborn', relation: 'son', name: 'Leo' })), 'Leo, newborn, son')
})

test('their sheet is a temperament, then what they are into lately; a newborn has only the temperament', () => {
  assert.equal(sheetText(child({})), 'Easygoing and quick to laugh. Lately into puddles.')
  assert.equal(sheetText(child({ likes: null })), 'Easygoing and quick to laugh.')
})

test('how they came folds under a line that says born or came home', () => {
  assert.equal(arrivalText(child({}), 'expecting_them', day), 'Born 2028-03-03')
  assert.equal(arrivalText(child({ arrived_on: '2029-01-10' }), 'adoption', day), 'Came home 2029-01-10')
})

test('who looks after them says who picked it and how long it lasts', () => {
  const view = { shown: true, children: [], care: 'part_time', care_how: 'seeded', care_now: true } as OursView
  assert.match(careHint(view, 'Mira Lane'), /^Picked by the app from Mira's work and your money\. Until the youngest/)
  assert.match(careHint({ ...view, care_how: 'set', care_now: false }, 'Mira'), /^You set this\. Once the youngest is at school/)
})

test('another child says when it can come up', () => {
  const view = { shown: true, wants: 'yes', romance: true } as FamilyView
  assert.match(anotherHint({ ...view, can_decide_another: false }, 'Mira'), /a year and a half after/)
  assert.match(anotherHint({ ...view, can_decide_another: true }, 'Mira'), /^Mira may bring it up/)
})

test('the Family life slider has four steps, easy kids first', () => {
  assert.deepEqual(FAMILY_LIFE_LEVELS.map((item) => item.label), ['Easy kids', 'Gentle', 'True to life', 'True-to-life chaos'])
})
