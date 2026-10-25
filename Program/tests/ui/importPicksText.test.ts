import assert from 'node:assert/strict'
import { test } from 'node:test'
import { anythingTicked, entryCount, owners, pickBody, startingPicks, type CharacterFile, type MapFile } from '../../src/features/character/importPicksText.ts'
import { broughtText } from '../../src/features/character/loreText.ts'

const entry = { title: 'Sarek', keywords: ['Sarek'], always: false, enabled: true, pattern: false, text: 'His father.' }
const spock: CharacterFile = {
  kind: 'character', format: 'Marinara Engine character', character: { name: 'Spock', about: 'A Vulcan officer.', more_about: false },
  picture: null, book: { name: 'Spock lore', format: 'Character lorebook', entries: [entry, { ...entry, title: 'Amanda' }] },
  unused: ["Creator's notes"], companions: [{ id: 'm', name: 'Mira' }], already: null,
}

test('everything starts ticked and goes as one import', () => {
  const picks = startingPicks(spock)
  assert.equal(picks.main, true)
  assert.deepEqual(pickBody(spock, picks), { character: true, picture: true, book: true, entries: null, lore_for: 'new' })
  assert.equal(entryCount(picks, spock.book!), 'All 2 entries')
})

test('only the lorebook goes to the world, or to the companion they already are', () => {
  const picks = { ...startingPicks(spock), main: false }
  assert.deepEqual(owners(spock, picks).options.map((option) => option.value), ['m', 'world'])
  assert.equal(pickBody(spock, picks).lore_for, 'world')
  const already = { ...spock, already: { id: 'm', name: 'Mira' } }
  const start = startingPicks(already)
  assert.equal(start.main, false)
  assert.equal(owners(already, start).chosen, 'm')
})

test('a few entries are sent by position, and nothing ticked cannot import', () => {
  const picks = { ...startingPicks(spock), entries: new Set([1]) }
  assert.deepEqual(pickBody(spock, picks).entries, [1])
  assert.equal(entryCount(picks, spock.book!), '1 of 2 entries')
  assert.equal(anythingTicked(spock, { ...picks, main: false, entries: new Set() }), false)
})

test('a world map that already came in starts with only its lore ticked', () => {
  const map: MapFile = { kind: 'map', format: 'Marinara world map', city: { name: 'Lisbon', counts: { neighborhoods: 3, places: 9, employers: 2 } },
    book: spock.book, already: 'Lisbon' }
  const picks = startingPicks(map)
  assert.equal(picks.main, false)
  assert.deepEqual(pickBody(map, picks), { city: false, book: true, entries: null })
  assert.equal(anythingTicked(map, { ...picks, book: false }), false)
})

test('lore brought for someone else says whose it is', () => {
  const book = { id: 'b', name: 'Spock lore', world: false, entries: 8, off: 0, owner: 'Spock' }
  assert.equal(broughtText({ format: 'x', picture: false, companion: null, book }), "Spock lore is now Spock's lore: 8 lore entries.")
  const made = broughtText({ format: 'Card', picture: false, companion: { version: { name: 'Dana', definition: { identity: '' } } },
    book: { ...book, world: true, owner: null } })
  assert.equal(made, 'Dana is here (from a Card). Their lorebook is now part of this world: 8 lore entries.')
})
