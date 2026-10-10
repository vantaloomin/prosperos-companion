import assert from 'node:assert/strict'
import { test } from 'node:test'
import { aroundText, personLine, placeGroups, sceneTime } from '../../src/features/story/storyText.ts'

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

test('unnamed people who read the same are counted, not repeated', () => {
  const local = (hood: string) => `a local from ${hood}`
  assert.equal(aroundText(['the barista', local('Little Italy'), local('Little Italy'), local('Harbor East'), local('Little Italy'), local('Fells Point')]),
    'The barista, three locals from Little Italy, a local from Harbor East and a local from Fells Point are here.')
  assert.equal(aroundText([local('Canton'), local('Canton')]), 'Two locals from Canton are here.')
  assert.equal(aroundText(['a neighbor waiting for the bus', 'a neighbor waiting for the bus']), 'Two neighbors waiting for the bus are here.')
  assert.equal(aroundText(['the barista', 'the barista', 'the waitress', 'the waitress']), 'Two baristas and two waitresses are here.')
  assert.equal(aroundText(['Dana, the barista', 'Dana, the barista']), 'Dana, the barista and Dana, the barista are here.')
})

test('places are grouped by neighborhood', () => {
  const place = (id: string, neighborhood: string) => ({ id, name: id, kind: 'cafe', neighborhood })
  assert.deepEqual(placeGroups([place('b', 'Canton'), place('a', 'Fells Point'), place('c', 'Canton')]).map(([hood, items]) => [hood, items.map((item) => item.id)]),
    [['Canton', ['b', 'c']], ['Fells Point', ['a']]])
})

test('a person met says how often and where they are now', () => {
  const person = { key: 'k', name: 'Dana Kim', role: 'barista', city: 'Baltimore', meetings: 3, last_met_at: '', notes: [],
    doing: 'working as the barista', place: { id: 'p', name: 'The Daily Grind', city_id: 'baltimore' } }
  assert.equal(personLine(person), 'Met 3 times · now working as the barista at The Daily Grind')
  assert.equal(personLine({ ...person, meetings: 1, doing: 'at home', place: null }), 'Met once · now at home')
  assert.equal(personLine({ ...person, doing: 'at their usual spot at The Daily Grind' }), 'Met 3 times · now at their usual spot at The Daily Grind')
})
