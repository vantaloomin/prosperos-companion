import assert from 'node:assert/strict'
import { test } from 'node:test'
import { byHood, historyLine, mainPin, sketch, suggestion, type CityMapData, type MapPlace } from '../../src/features/map/mapText.ts'

const place = (id: string, hood: string, pins: MapPlace['pins'] = []): MapPlace => ({
  id, name: id, kind: 'cafe', hood: hood === 'a' ? 'Alder' : 'Birch', hood_id: hood, lat: 0, lon: 0, approx: true, pins, spots: [], history: [], regulars: [],
})

test('a place shows its most telling pin', () => {
  assert.equal(mainPin({ pins: ['recent', 'usual'] }), 'usual')
  assert.equal(mainPin({ pins: ['recent', 'scene'] }), 'scene')
  assert.equal(mainPin({ pins: [] }), 'place')
})

test('history, suggestions and the list read plainly', () => {
  assert.equal(historyLine({ summary: 'Coffee after work.', at: '2026-10-06T22:00:00Z' }, 'UTC'), 'Coffee after work. · Tue')
  assert.equal(suggestion({ name: 'Blue Moon', kind: 'cafe' }), 'Want to go to Blue Moon this weekend?')
  assert.equal(suggestion({ name: 'The Owl', kind: 'bar' }), 'Want to go to The Owl one night this week?')
  assert.deepEqual(byHood([place('z', 'a'), place('y', 'b'), place('x', 'a', ['usual'])]).map(([hood, items]) => [hood, items.map((item) => item.id)]),
    [['Alder', ['x', 'z']], ['Birch', ['y']]])
})

test('the sketch keeps neighbourhoods apart, places inside them', () => {
  const data: CityMapData = {
    city: { id: 'c', name: 'C', lat: 40, lon: -70, real: false }, story: false,
    hoods: [{ id: 'a', name: 'Alder', lat: 40, lon: -70, next: ['b'] }, { id: 'b', name: 'Birch', lat: 40.0001, lon: -70.0001, next: ['a'] }],
    places: [place('p1', 'a'), place('p2', 'a'), place('p3', 'b')],
  }
  const { bubbles, width, height } = sketch(data)
  const [a, b] = bubbles
  assert.ok(Math.hypot(a.x - b.x, a.y - b.y) >= a.r + b.r)
  assert.equal(a.places.length, 2)
  for (const bubble of bubbles) for (const spot of bubble.places) assert.ok(Math.hypot(spot.x - bubble.x, spot.y - bubble.y) < bubble.r)
  assert.ok(width > 0 && height > 0 && bubbles.every((bubble) => bubble.x - bubble.r >= 0 && bubble.y - bubble.r >= 0))
})
