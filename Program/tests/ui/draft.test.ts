import assert from 'node:assert/strict'
import { test } from 'node:test'
import { addHood, addPlace, briefLine, changeCity, changeItem, inHood, mapData, redrawsAll, removeItem, takeSection, uniqueId, type Brief, type Definition, type Work } from '../../src/features/draft/draftText.ts'

const item = (id: string, neighborhood?: string, extra: Record<string, unknown> = {}) => ({ id, name: id, summary: `${id}.`, ...(neighborhood ? { neighborhood } : {}), ...extra })
const hood = (id: string, lat: number, transit: string[] = ['walk']) => ({ ...item(id), lat, lon: 0, transit })

function town(): Definition {
  return {
    id: 'ridgemouth', name: 'Ridgemouth', summary: 'A town.', region: 'Maine', country: 'United States', era: 'jazz-age', lat: 0, lon: 0,
    neighborhoods: [hood('docks', 0), hood('hill', 0.01, ['walk', 'tram'])],
    places: [item('pier', 'docks', { kind: 'docks' }), item('chowder', 'docks', { kind: 'restaurant' }), item('chapel', 'hill', { kind: 'temple' })],
    employers: [item('cannery', 'docks'), item('school', 'hill')],
    career_hubs: [{ ...item('waterfront'), neighborhoods: ['docks', 'hill'] }],
    transit: [item('walk'), item('tram')],
    annual_events: [{ ...item('regatta', 'docks'), months: [7] }],
    local_color: [{ ...item('chowder-recipe', undefined, { kind: 'dish' }), places: ['chowder'] }],
  }
}

const brief: Brief = { line: 'a cold fishing town, 1920s', era: 'jazz-age', group: '1920s', aboard: false, water: 'sea', biome: 'cold', size: 'town', year: null, name: null, anchor: 'pellmouth', donor: 'pellmouth' }

test('rolling one list again keeps every change elsewhere and drops what points at removed parts', () => {
  const current = changeItem(removeItem(town(), 'neighborhoods', 'hill'), 'places', 'pier', { name: 'Old Pier' })
  const fresh = town()
  fresh.employers = [item('net-loft', 'docks'), item('observatory', 'hill')]
  const rolled = takeSection(current, fresh, 'employers')
  assert.deepEqual(rolled.employers.map((entry) => entry.id), ['net-loft'])
  assert.equal(rolled.places.find((entry) => entry.id === 'pier')?.name, 'Old Pier')
  assert.deepEqual(rolled.career_hubs[0].neighborhoods, ['docks'])
  assert.ok(redrawsAll('hoods') && redrawsAll('name') && !redrawsAll('places'))
})

test('rolling the ways about again gives each part of town its new lines', () => {
  const fresh = town()
  fresh.transit = [item('walk'), item('ferry')]
  fresh.neighborhoods = [hood('docks', 0, ['walk', 'ferry']), hood('hill', 0.01, ['walk'])]
  const rolled = takeSection(changeItem(town(), 'neighborhoods', 'hill', { name: 'Chapel Hill' }), fresh, 'transit')
  assert.deepEqual(rolled.neighborhoods.map((entry) => [entry.name, entry.transit]), [['docks', ['walk', 'ferry']], ['Chapel Hill', ['walk']]])
})

test('removing a part of town takes its places and employers with it and moves its events to all over town', () => {
  const definition = town()
  assert.deepEqual(inHood(definition, 'docks'), { places: 2, employers: 1 })
  const left = removeItem(definition, 'neighborhoods', 'docks')
  assert.deepEqual(left.places.map((entry) => entry.id), ['chapel'])
  assert.deepEqual(left.employers.map((entry) => entry.id), ['school'])
  assert.deepEqual(left.career_hubs[0].neighborhoods, ['hill'])
  assert.equal(left.annual_events[0].neighborhood, undefined)
  assert.deepEqual(left.local_color[0].places, [])
})

test('removing a place or a way about leaves nothing pointing at it', () => {
  assert.deepEqual(removeItem(town(), 'places', 'chowder').local_color[0].places, [])
  assert.deepEqual(removeItem(town(), 'transit', 'tram').neighborhoods[1].transit, ['walk'])
})

test('new places and parts of town get ids of their own and copy their neighbours', () => {
  const added = addPlace(town(), 'hill')
  const place = added.definition.places.find((entry) => entry.id === added.id)
  assert.equal(added.id, 'new-place')
  assert.equal(place?.neighborhood, 'hill')
  assert.equal(place?.kind, 'temple')
  assert.equal(addPlace(added.definition, 'hill').id, 'new-place-2')
  const grown = addHood(town())
  assert.equal(grown.id, 'new-neighborhood')
  assert.equal(grown.definition.places.filter((entry) => entry.neighborhood === grown.id).length, 1)
  assert.equal(uniqueId('The Docks', ['the-docks']), 'the-docks-2')
})

test('until it is saved, a place takes its id from its name', () => {
  const work: Work = { line: brief.line, seed: '1', rolls: {}, definition: town(), brief, edited: false }
  assert.equal(changeCity(work, { name: 'Kelport' }).id, 'kelport')
  assert.equal(changeCity({ ...work, saved: { id: 'ridgemouth', revision: 1 } }, { name: 'Kelport' }).id, 'ridgemouth')
})

test('the map shows every place in its part of town and the facts read plainly', () => {
  const data = mapData(town())
  assert.equal(data.places.length, 3)
  assert.ok(data.places.every((entry) => entry.approx && !entry.pins.length))
  assert.deepEqual(data.hoods.map((entry) => entry.next), [['hill'], ['docks']])
  assert.equal(briefLine(brief, town()), '1920s · Town on the sea · Cold')
  assert.equal(briefLine(null, town()), '1920s · 2 neighborhoods')
})
