import assert from 'node:assert/strict'
import { test } from 'node:test'
import { categoryOf, cityFacts, definitionOf, exportName, groupNotes, matchesCity, ownCityFor, parseDefinition, shelveCities, slugify, type CityListing } from '../../src/features/world/cityText.ts'

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

test('cities shelve as Real / Modern, Other Eras, Fictional and Custom, each sorted by name', () => {
  const shelves = shelveCities([
    city({ id: 'z', name: 'Zed', origin: 'user', category: 'custom' }), city({ category: 'real' }),
    city({ id: 'oz', name: 'The Emerald City', category: 'fictional' }), city({ id: 'a', name: 'Arden', origin: 'user', category: 'custom' }),
    city({ id: 'old', name: 'Old Server City' }),
  ])
  assert.deepEqual(shelves.map((shelf) => [shelf.title, shelf.cities.map((item) => item.name)]), [
    ['Real / Modern', ['Baltimore', 'Old Server City']], ['Other Eras', []], ['Fictional', ['The Emerald City']], ['Custom', ['Arden', 'Zed']],
  ])
  assert.equal(categoryOf({ name: 'x', category: 'something-else' }), 'real')
})

test('the city search matches name, other names, region and country, ignoring accents and case', () => {
  const ellerbruck = city({ name: 'Ellerbrück', region: 'Hesse', country: 'a small German principality', aliases: ['the market town'] })
  assert.ok(matchesCity(ellerbruck, 'ellerbruck'))
  assert.ok(matchesCity(ellerbruck, ' HESSE '))
  assert.ok(matchesCity(ellerbruck, 'german'))
  assert.ok(matchesCity(ellerbruck, 'market'))
  assert.ok(matchesCity(ellerbruck, ''))
  assert.ok(!matchesCity(ellerbruck, 'gotham'))
})

test('facts read naturally', () => {
  assert.equal(cityFacts(city()), 'Real city · modern · 21 neighborhoods, 124 places')
  assert.equal(cityFacts(city({ setting: 'original', counts: { ...city().counts, neighborhoods: 1, places: 1 } })), 'Original setting · modern · 1 neighborhood, 1 place')
})


test('notes that say the same about several places become one line', () => {
  const many = Array.from({ length: 8 }, (_, index) => `Mill ${index + 1}: filled in cost as '$'.`)
  assert.deepEqual(groupNotes(['Timezone set to UTC.', 'Bluebird Diner: filled in cost as \'$\'.', 'Oak Hall: ignored the field "x", which the app does not use.', 'Pier: filled in cost as \'$\'.']),
    ['Timezone set to UTC.', "Bluebird Diner and Pier: filled in cost as '$'.", 'Oak Hall: ignored the field "x", which the app does not use.'])
  assert.deepEqual(groupNotes(many), ["Mill 1, Mill 2, Mill 3, Mill 4, Mill 5 and 3 more: filled in cost as '$'."])
})

test('a city file with the id of one of your own cities updates that city in place', () => {
  const mine = city({ id: 'uss-enterprise', name: 'USS Enterprise', origin: 'user', builtin: false })
  const shelf = [city(), mine]
  assert.equal(ownCityFor('{"id": "uss-enterprise", "name": "USS Enterprise"}', shelf), mine)
  assert.equal(ownCityFor('{"id": "baltimore"}', shelf), null)
  assert.equal(ownCityFor('{"id": "somewhere-else"}', shelf), null)
  assert.equal(ownCityFor('{"id": ', shelf), null)
})
