import assert from 'node:assert/strict'
import { test } from 'node:test'
import { givenName, steppedBack } from '../../src/features/character/castText.ts'

test('a companion who stepped back says when', () => {
  assert.match(steppedBack({ stepped_back_at: '2026-10-05T12:00:00Z' }), /^Stepped back on /)
  assert.equal(steppedBack({ stepped_back_at: null }), '')
})

test('buttons use the given name', () => {
  assert.equal(givenName('Dana Kim'), 'Dana')
  assert.equal(givenName('  Mira '), 'Mira')
})
