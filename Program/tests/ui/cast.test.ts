import assert from 'node:assert/strict'
import { test } from 'node:test'
import { givenName, steppedBack, townSeedText } from '../../src/features/character/castText.ts'

test('a companion who stepped back says when', () => {
  assert.match(steppedBack({ stepped_back_at: '2026-10-05T12:00:00Z' }), /^Stepped back on /)
  assert.equal(steppedBack({ stepped_back_at: null }), '')
})

test('buttons use the given name', () => {
  assert.equal(givenName('Dana Kim'), 'Dana')
  assert.equal(givenName('  Mira '), 'Mira')
})

test('the townsfolk choice says whose people they are', () => {
  assert.match(townSeedText('Mira', false).about, /same townsfolk as anyone else/)
  assert.match(townSeedText('Mira', true).about, /drawn just for Mira/)
  assert.match(townSeedText('Mira', true).warning, /^Everyone Mira has met/)
  const champions = townSeedText('Sett', true, ['Ahri', 'Akali', 'Hwei', 'Irelia'])
  assert.match(champions.about, /drawn just for Sett\. Ahri, Akali and 2 other well-known people are there, whatever townsfolk Sett has\.$/)
  assert.match(champions.warning, /The city's well-known people stay, and Sett still knows the ones they've met\./)
  assert.match(townSeedText('Sett', false, ['Ahri']).about, /Ahri is there, whatever townsfolk Sett has\.$/)
  assert.match(townSeedText('Sett', false, ['Ahri', 'Akali', 'Hwei']).about, /Ahri, Akali and Hwei are there/)
})
