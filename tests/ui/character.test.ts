import assert from 'node:assert/strict'
import { test } from 'node:test'
import { cleanDefinition, completeDefinition, emptyDefinition, parseInterests } from '../../src/features/character/definition.ts'

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
