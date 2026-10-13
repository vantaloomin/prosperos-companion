import assert from 'node:assert/strict'
import { test } from 'node:test'
import { LOOKS_LEVELS, changeLine, fixedLine } from '../../src/features/character/looksLatelyText.ts'

test('the Realism slider has a word for every level the server accepts (0 to 3)', () => {
  assert.deepEqual(LOOKS_LEVELS.map((level) => level.label), ['Never', 'Now and then', 'Like real life', 'Often'])
})

test('looks the user wrote are named in plain words', () => {
  assert.equal(fixedLine([]), null)
  assert.equal(fixedLine(['hair']), 'Staying exactly as you wrote it: hair.')
  assert.equal(fixedLine(['hair', 'nails', 'feature']), 'Staying exactly as you wrote them: hair, nails and what people notice about them.')
  assert.equal(changeLine('dyed her hair copper red'), 'Dyed her hair copper red.')
})
