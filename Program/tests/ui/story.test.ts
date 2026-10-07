import assert from 'node:assert/strict'
import { test } from 'node:test'
import { aroundText, placeGroups, sceneTime } from '../../src/features/story/storyText.ts'

test('the scene time is the city clock as written', () => {
  assert.equal(sceneTime('2026-10-06T09:05'), 'Tuesday, 9:05 am')
  assert.equal(sceneTime('2026-10-06T00:30'), 'Tuesday, 12:30 am')
  assert.equal(sceneTime('2026-10-06T21:40'), 'Tuesday, 9:40 pm')
})

test('who is around reads as a sentence', () => {
  assert.equal(aroundText([]), 'Nobody you would notice is here.')
  assert.equal(aroundText(['the barista']), 'The barista is here.')
  assert.equal(aroundText(['the barista', 'a regular', 'a neighbor']), 'The barista, a regular and a neighbor are here.')
})

test('places are grouped by neighborhood', () => {
  const place = (id: string, neighborhood: string) => ({ id, name: id, kind: 'cafe', neighborhood })
  assert.deepEqual(placeGroups([place('b', 'Canton'), place('a', 'Fells Point'), place('c', 'Canton')]).map(([hood, items]) => [hood, items.map((item) => item.id)]),
    [['Canton', ['b', 'c']], ['Fells Point', ['a']]])
})
