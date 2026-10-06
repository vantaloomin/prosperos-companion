import assert from 'node:assert/strict'
import { test } from 'node:test'
import { cityFacts, definitionOf, exportName, groupCities, parseDefinition, slugify, type CityListing } from '../../src/features/world/cityText.ts'

const city = (extra: Partial<CityListing> = {}): CityListing => ({
  id: 'baltimore', name: 'Baltimore', region: 'Maryland', country: 'US', setting: 'real', era: 'modern', summary: '', basis: '',
  counts: { neighborhoods: 21, places: 124, colleges: 9, employers: 16, annual_events: 12 }, builtin: true, origin: 'builtin',
  distribution: 'public', ...extra,
})

test('slugs are lowercase ascii ids', () => {
  assert.equal(slugify('My Ellerbrück!'), 'my-ellerbruck')
  assert.equal(slugify('  --New   York-- '), 'new-york')
  assert.equal(slugify('!!!'), '')
})

test('derived keys are dropped from an exported definition', () => {
  assert.deepEqual(definitionOf({ id: 'x', data_version: 'abc', revision: 2, origin: 'user', builtin: false, name: 'X' }), { id: 'x', name: 'X' })
  assert.equal(exportName('my-city'), 'my-city.json')
})

test('the editor text must be a JSON object', () => {
  assert.deepEqual(parseDefinition('{"id": "a"}'), { ok: true, value: { id: 'a' } })
  assert.equal(parseDefinition('[1]').ok, false)
  const broken = parseDefinition('{"id": ')
  assert.equal(broken.ok, false)
  assert.match(broken.ok ? '' : broken.error, /not valid JSON/)
})

test('cities group by origin and sort by name', () => {
  const groups = groupCities([city({ id: 'z', name: 'Zed', origin: 'user' }), city(), city({ id: 'a', name: 'Arden', origin: 'user' })])
  assert.deepEqual(groups.user.map((item) => item.name), ['Arden', 'Zed'])
  assert.equal(groups.builtin.length, 1)
  assert.deepEqual(groups.pack, [])
})

test('facts read naturally', () => {
  assert.equal(cityFacts(city()), 'Real city · modern · 21 neighbourhoods, 124 places')
  assert.equal(cityFacts(city({ setting: 'original', counts: { ...city().counts, neighborhoods: 1, places: 1 } })), 'Original setting · modern · 1 neighbourhood, 1 place')
})
