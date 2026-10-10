import assert from 'node:assert/strict'
import { test } from 'node:test'
import { emptyLooks, heightLabel, numberChoices, weightLabel } from '../../src/features/character/looksText.ts'

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
