import assert from 'node:assert/strict'
import { test } from 'node:test'
import { childLabel, childLine, expectingLabel, expectingLine, FAMILY_LEVELS } from '../../src/features/character/familiesText.ts'
import type { CircleChild, CirclePerson } from '../../src/types.ts'

const child = (changes: Partial<CircleChild>): CircleChild => ({
  id: 'c1', name: 'Mia', pronouns: 'she/her', born_on: '2026-03-01', age: 2, age_text: '2', relation: 'niece', title: 'family', ...changes,
})

test('a child reads as who they are to the companion, or whose they are', () => {
  assert.equal(childLine(child({}), 'Ana', 'Dana Reyes'), "Mia, 2, Dana's niece")
  assert.equal(childLine(child({ age_text: 'a newborn', relation: null, title: 'friend', pronouns: 'he/him', name: 'Leo' }), 'Sam', 'Dana'), "Leo, newborn, Sam's son")
  assert.equal(childLine(child({ age_text: '7 months old', relation: 'goddaughter', title: 'godchild' }), 'Sam', 'Dana'), "Mia, 7 months old, Dana's goddaughter")
})

test("the companion's own child reads as theirs and their partner's", () => {
  assert.equal(childLine(child({ age_text: 'a newborn', relation: 'daughter', own: true, name: 'Ivy' }), 'Tyler Battle', 'Dana Reyes'), "Ivy, newborn, Dana and Tyler's daughter")
})

test('a baby is labelled Baby until their first birthday, then Child', () => {
  assert.equal(childLabel(child({ age_text: '7 months old' })), 'Baby')
  assert.equal(childLabel(child({ age_text: '2' })), 'Child')
})

test('a due month shows while they are expecting', () => {
  assert.equal(expectingLine({ expecting: 'March' } as CirclePerson), 'a baby, due in March')
  assert.equal(expectingLine({ expecting: null } as CirclePerson), null)
  assert.equal(expectingLine({ expecting: 'May', adopting: true } as CirclePerson), 'a baby, coming home around May')
  assert.equal(expectingLabel({ expecting: 'May', adopting: true } as CirclePerson), 'Adopting')
  assert.equal(expectingLabel({ expecting: 'May' } as CirclePerson), 'Expecting')
})

test('the slider has four steps, the third true to life', () => {
  assert.equal(FAMILY_LEVELS.length, 4)
  assert.equal(FAMILY_LEVELS[2].label, 'True to life')
})
