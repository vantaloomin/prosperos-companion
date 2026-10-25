import assert from 'node:assert/strict'
import { test } from 'node:test'
import { asChip } from '../../src/features/character/ownWordsText.ts'

test('typed turn-ons read mid-sentence: a first capital goes unless it looks like a name', () => {
  assert.equal(asChip('  Smoking.  '), 'smoking')
  assert.equal(asChip('Someone   who reads to them'), 'someone who reads to them')
  assert.equal(asChip('BBQ dates'), 'BBQ dates')
  assert.equal(asChip('McKenna-style banter'), 'McKenna-style banter')
  assert.equal(asChip('   '), '')
})
