import assert from 'node:assert/strict'
import { test } from 'node:test'
import { clockLength } from '../../src/features/conversation/voiceLength.ts'

test('a voice note length reads like a clock', () => {
  assert.equal(clockLength(0), '0:00')
  assert.equal(clockLength(6.6), '0:07')
  assert.equal(clockLength(75), '1:15')
  assert.equal(clockLength(-3), '0:00')
})
