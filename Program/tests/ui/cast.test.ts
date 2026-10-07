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
})
