import assert from 'node:assert/strict'
import { test } from 'node:test'
import { outcomeSummary } from '../../src/features/character/familyText.ts'

test('each "Why it went this way" under a journey says which outcome it is', () => {
  const adoption = ['wait', 'match'].map((key) => outcomeSummary(key, 'adoption'))
  assert.deepEqual(adoption, ['Why the wait for a match is this long', 'How old the child will be'])
  const pregnancy = ['soon', 'turn'].map((key) => outcomeSummary(key, 'expecting_them'))
  assert.equal(new Set(pregnancy).size, 2)
  assert.equal(outcomeSummary('turn', 'expecting_you'), 'Why the pregnancy went this way')
  assert.equal(outcomeSummary('fostered', 'fostering'), 'Whether fostering leads to adopting')
  assert.equal(outcomeSummary('', 'adoption'), 'Why it went this way')
})
