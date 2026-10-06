import assert from 'node:assert/strict'
import { test } from 'node:test'
import { cleanDefinition, completeDefinition, emptyDefinition, listTexts, parseInterests, parseLines } from '../../src/features/character/definition.ts'
import { fieldValue, toggleVibe, withField } from '../../src/features/character/drafting.ts'

test('interests split on commas and lines, trimmed and without repeats', () => {
  assert.deepEqual(parseInterests('Tea, hiking\nTea , , Jazz'), ['Tea', 'hiking', 'Jazz'])
})

test('a new character starts as a friendship with no emotional traits', () => {
  const definition = emptyDefinition('Europe/Lisbon')
  assert.equal(definition.relationship, 'friendship')
  assert.deepEqual(definition.emotional_traits, [])
  assert.equal(definition.timezone, 'Europe/Lisbon')
})

test('blank trait rows are dropped when saving', () => {
  const definition = { ...emptyDefinition(), name: ' Mira ', emotional_traits: [{ name: ' ', intensity: 'mild' as const, note: '' }, { name: 'Jealousy ', intensity: 'strong' as const, note: ' teasing ' }] }
  const saved = cleanDefinition(definition, 'Tea')
  assert.equal(saved.name, 'Mira')
  assert.deepEqual(saved.emotional_traits, [{ name: 'Jealousy', intensity: 'strong', note: 'teasing' }])
  assert.deepEqual(saved.interests, ['Tea'])
})

test('older saved versions without traits still open in the form', () => {
  assert.deepEqual(completeDefinition({ name: 'Mira' }).emotional_traits, [])
})

test('skills and flaws are one per line, so an item can contain a comma', () => {
  assert.deepEqual(parseLines('- Fixes bikes, slowly\n\n• Fixes bikes, slowly\nBakes bread'), ['Fixes bikes, slowly', 'Bakes bread'])
  const saved = cleanDefinition({ ...emptyDefinition(), name: 'Mira' }, '', '', { skills: 'Knits\nKnits', flaws: 'Late, always' })
  assert.deepEqual([saved.skills, saved.flaws], [['Knits'], ['Late, always']])
  assert.deepEqual(completeDefinition({ name: 'Mira' }).flaws, [])
})

test('vibe chips add and remove themselves without touching typed vibes', () => {
  assert.equal(toggleVibe('', 'Blunt'), 'Blunt')
  assert.equal(toggleVibe('likes trains, Blunt', 'blunt'), 'likes trains')
  assert.equal(toggleVibe('likes trains', 'Nerdy'), 'likes trains, Nerdy')
})

test('a rewritten list field lands in the text the form edits, and can be put back', () => {
  const definition = { ...emptyDefinition(), flaws: ['Late'], identity: 'A nurse.' }
  const form = { definition, texts: listTexts(definition) }
  const rewritten = withField(form, 'flaws', ['Holds grudges', 'Cancels plans'])
  assert.equal(rewritten.texts.flaws, 'Holds grudges\nCancels plans')
  assert.equal(withField(rewritten, 'flaws', fieldValue(form, 'flaws')).texts.flaws, 'Late')
  assert.equal(withField(form, 'identity', 'A nurse who runs.').definition.identity, 'A nurse who runs.')
  assert.equal(withField(form, 'life_themes', ['her brother', 'night shifts']).texts.themes, 'her brother, night shifts')
})
