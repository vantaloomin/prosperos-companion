import assert from 'node:assert/strict'
import { test } from 'node:test'
import { decadeHint, emptyLooks, emptyText, heightLabel, keepsAgeHint, numberChoices, weightLabel } from '../../src/features/character/looksText.ts'

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

test('an empty field before the first save says it is picked, short enough for a phone', () => {
  assert.equal(emptyText(false, false, null), 'Picked for them if left empty')
  assert.equal(emptyText(true, false, 'brown'), 'Left empty: brown')
})

test('an identity in a decade the age has left says so on the Character page', () => {
  assert.equal(decadeHint('In her thirties, a translator.', 47), 'thirties')
  assert.equal(keepsAgeHint({ name: 'Maya Ortiz' }, 35, 47, 'thirties'),
    "Maya is 47 now, though their description says thirties, and turns a year older on each birthday. Turn this on for a character who shouldn't age.")
  assert.equal(decadeHint('In her late Thirties.', 39), '')
  assert.equal(decadeHint('34. A translator.', 47), '')
  assert.equal(decadeHint('In his forties.', null), '')
})
