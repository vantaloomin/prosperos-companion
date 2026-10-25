import assert from 'node:assert/strict'
import { test } from 'node:test'
import { turnedDown } from '../../src/features/character/drafting.ts'

test('a refused draft says what happened and what to do, with the service’s own words', () => {
  assert.equal(turnedDown('The service turned down the request (HTTP 400). It said: "Your organization must be verified."'),
    'Your text model turned down the request, so nothing was written yet. The service said: "Your organization must be verified." Pick another model in Settings, or fill in the form yourself.')
  assert.equal(turnedDown('The service turned down the request (HTTP 422).'),
    'Your text model turned down the request, so nothing was written yet. Pick another model in Settings, or fill in the form yourself.')
  assert.equal(turnedDown('The service reached a rate or usage limit. Try again when it is available.'), 'The service reached a rate or usage limit. Try again when it is available.')
})
