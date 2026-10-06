import assert from 'node:assert/strict'
import { test } from 'node:test'
import { nameMatches, removedSummary } from '../../src/features/character/startOverText.ts'

const preview = { name: 'Mira', messages: 12, memories: 1, timelines: 2, images: 0, versions: 3, adapters: 1, references: 0, training: false }

test('starting over lists the history; deleting adds who they are', () => {
  assert.equal(removedSummary(preview, 'reset'), '12 messages, 1 memory, 0 pictures and all 2 timelines')
  assert.equal(removedSummary(preview, 'delete'), '12 messages, 1 memory, 0 pictures, all 2 timelines, 3 character versions and 1 adapter')
  assert.equal(removedSummary({ ...preview, timelines: 1 }, 'reset'), '12 messages, 1 memory and 0 pictures')
})

test('the typed name ignores case and spaces but never matches empty', () => {
  assert.ok(nameMatches(' mira ', 'Mira'))
  assert.ok(!nameMatches('Mir', 'Mira'))
  assert.ok(!nameMatches('  ', ''))
})
