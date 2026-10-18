import assert from 'node:assert/strict'
import { test } from 'node:test'
import { emptyLooks, heightLabel, keepsAgeHint, numberChoices, weightLabel } from '../../src/features/character/looksText.ts'

test('heights and weights read in both units', () => {
  assert.equal(heightLabel(170), `5'7" (170 cm)`)
  assert.equal(weightLabel(68), '150 lb (68 kg)')
})

test('every choice is one the server accepts (companion/models.py Looks)', () => {
  for (const [kind, low, high] of [['age', 18, 120], ['height', 120, 230], ['weight', 35, 250]] as const) {
    const choices = numberChoices(kind)
    assert.ok(choices.every((value) => value >= low && value <= high), kind)
    assert.equal(new Set(choices).size, choices.length, kind)
  }
})

test('an empty sheet leaves every field for the app to draw', () => {
  assert.ok(Object.values(emptyLooks()).every((value) => value === null || value === ''))
})

test('the Keeps their age hint reads right for a named companion and one not named yet', () => {
  const named = { name: 'Dana Reyes' }
  assert.equal(keepsAgeHint({ ...named, keeps_age: true }, 34, 36), 'Dana stays 36, however many birthdays pass.')
  assert.equal(keepsAgeHint(named, 34, 36), "Dana is 36 now and turns a year older on each birthday. Turn this on for a character who shouldn't age.")
  const unnamed = { name: '' }
  assert.equal(keepsAgeHint({ ...unnamed, keeps_age: true }, null, null), 'They stay the age they are now, however many birthdays pass.')
  assert.equal(keepsAgeHint({ ...unnamed, keeps_age: true }, 30, null), 'They stay 30, however many birthdays pass.')
  assert.equal(keepsAgeHint(unnamed, 30, null), "They turn a year older on each birthday. Turn this on for a character who shouldn't age.")
})
