import assert from 'node:assert/strict'
import { test } from 'node:test'
import { byHood, historyLine, mainPin, suggestion, type CityMapData, type MapPlace } from '../../src/features/map/mapText.ts'
import { drawn, inside, labels, pathOf } from '../../src/features/map/drawn.ts'

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

const city = (water: CityMapData['water'] = []): CityMapData => ({
  city: { id: 'c', name: 'C', lat: 40, lon: -70, real: false }, story: false, water,
  hoods: [{ id: 'a', name: 'Alder', lat: 40, lon: -70, next: ['b'] }, { id: 'b', name: 'Birch', lat: 40.0001, lon: -70.0001, next: ['a'] },
    { id: 'c', name: 'Cedar', lat: 40.01, lon: -69.99, next: ['b'] }],
  places: [place('p1', 'a'), place('p2', 'a'), place('p3', 'b'), place('p4', 'c', ['home'])],
})

test('the drawn map gives each neighbourhood its own ground, with its places on its streets', () => {
  const map = drawn(city())
  assert.equal(map.districts.length, 3)
  for (const district of map.districts) {
    assert.ok(district.outline.length >= 3)
    assert.ok(inside({ x: district.x, y: district.y }, district.outline))
    for (const spot of district.places) assert.ok(inside(spot, district.outline), `${spot.place.id} sits inside ${district.name}`)
    for (const point of district.outline) assert.ok(point.x >= 0 && point.y >= 0 && point.x <= map.width && point.y <= map.height)
  }
  assert.equal(map.districts[0].places.length, 2)
  // Main roads join districts that share a border, so every neighbourhood is on one.
  for (const district of map.districts) assert.ok(map.roads.some((road) => road.id.split('|').includes(district.id)), district.name)
})

test('neighbourhoods on the drawn map never share ground', () => {
  const { districts } = drawn(city())
  for (const one of districts) for (const other of districts) if (one !== other) assert.ok(!inside({ x: one.x, y: one.y }, other.outline))
})

test('the drawn map is the same every time, and draws the water the city names', () => {
  const water = [{ kind: 'sea' as const, name: 'Grey Sea', side: 'south' as const, points: [], width_km: 0.3 },
    { kind: 'river' as const, name: 'Ash', side: null, points: [[40.008, -70.002], [40.004, -69.995], [40.0, -69.99]] as [number, number][], width_km: 0.2 }]
  const [first, second] = [drawn(city(water)), drawn(city(water))]
  assert.deepEqual(first, second)
  assert.ok(first.height > drawn(city()).height, 'room for the sea')
  assert.deepEqual(first.water.map((item) => [item.kind, item.name]), [['sea', 'Grey Sea'], ['river', 'Ash']])
  assert.match(pathOf(first.water[1].path, false, true), /^M-?[\d.]+ -?[\d.]+C/)
})

test('names on the drawn map do not run into each other', () => {
  const crowded = city([{ kind: 'river', name: 'The Long Winding River', side: null, width_km: 0.05, points: [[40, -70.002], [40.005, -69.995], [40.01, -69.99]] }])
  crowded.places = Array.from({ length: 30 }, (_, index) => ({ ...place(`p${index}`, index % 2 ? 'a' : 'b', [index % 3 ? 'usual' : 'recent']), name: `A rather long place name ${index}` }))
  const laid = labels(drawn(crowded))
  const box = (label: (typeof laid)[number]) => {
    const width = label.text.length * 6.8, left = label.anchor === 'start' ? label.x : label.anchor === 'end' ? label.x - width : label.x - width / 2
    return { left, right: left + width, top: label.y - 11, bottom: label.y + 2 }
  }
  const shown = laid.filter((label) => label.shown)
  shown.forEach((a, index) => shown.slice(index + 1).forEach((b) => {
    const one = box(a), two = box(b)
    assert.ok(one.right <= two.left || two.right <= one.left || one.bottom <= two.top || two.bottom <= one.top, `${a.text} clears ${b.text}`)
  }))
  assert.deepEqual(laid.filter((label) => label.kind === 'district').map((label) => label.shown), [true, true, true])
  assert.ok(laid.some((label) => label.kind === 'place' && label.shown && label.anchor !== 'start'), 'a name in the way moves to the other side of its pin')
  assert.ok(laid.some((label) => !label.shown), 'a name with no room is left off')
  assert.deepEqual(labels(drawn(crowded)), laid)
})
