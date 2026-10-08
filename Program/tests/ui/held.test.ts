import assert from 'node:assert/strict'
import { test } from 'node:test'
import { isHeld, releaseHeld, waitsUntilLater } from '../../src/features/conversation/held.ts'
import { activityLine, nextChange } from '../../src/features/conversation/activity.ts'
import { lastUserMessage } from '../../src/features/conversation/turns.ts'
import type { Message } from '../../src/types.ts'

const message = (extra: Partial<Message>): Message => ({
  id: 'm', timeline_id: 't', seq: 2, role: 'companion', text: 'full reply', reply_to: 'u', status: 'complete', active: true,
  redacted: false, error: null, character_version_id: null, created_at: '2026-10-05T10:00:00Z', completed_at: null, ...extra,
})

test('a reply is held until its time', () => {
  const held = message({ held_until: '2026-10-05T10:30:00Z', held_line: 'brb, boss is here' })
  assert.equal(isHeld(held, Date.parse('2026-10-05T10:10:00Z')), true)
  assert.equal(isHeld(held, Date.parse('2026-10-05T10:31:00Z')), false)
  assert.equal(isHeld(message({}), 0), false)
})

test('a reply shown at once shows replies held before it', () => {
  const released = releaseHeld([message({ held_until: '2099-01-01T00:00:00Z' }), message({ id: 'n', seq: 5, held_until: '2099-01-01T00:00:00Z' })], 4)
  assert.deepEqual(released.map((item) => item.held_until), [null, '2099-01-01T00:00:00Z'])
})

test('a held reply that failed is not kept out of sight', () => {
  const now = Date.parse('2026-10-05T10:10:00Z')
  const held = { held_until: '2026-10-05T10:30:00Z' }
  assert.equal(waitsUntilLater(message({ ...held, status: 'streaming' }), now), true)
  assert.equal(waitsUntilLater(message({ ...held, status: 'complete' }), now), true)
  assert.equal(waitsUntilLater(message({ ...held, status: 'failed', error: 'The reply reached the configured time limit.' }), now), false)
  assert.equal(waitsUntilLater(message({ ...held, status: 'incomplete' }), now), false)
})

test('the activity line says what the app is doing, never that the companion is away', () => {
  const now = Date.parse('2026-10-05T10:10:00Z')
  const user = message({ id: 'u', seq: 1, role: 'user', reply_to: null })
  const writing = message({ status: 'streaming', text: '' })
  assert.equal(activityLine([user], {}, true, now), 'Sending…')
  assert.equal(activityLine([user, writing], {}, false, now), 'Getting a reply ready…')
  assert.equal(activityLine([user, writing], { m: 'looking' }, false, now), 'Looking at your picture…')
  assert.equal(activityLine([user, writing], { m: 'waiting' }, false, now), 'Waiting for the model to be free…')
  assert.equal(activityLine([user, writing], { m: 'writing' }, false, now), 'Writing a reply…')
  const later = message({ status: 'complete', held_until: '2026-10-05T10:30:00Z' })
  assert.equal(activityLine([user, later], {}, false, now), 'Delivered')
  assert.equal(activityLine([user, { ...writing, held_until: later.held_until }], { m: 'writing' }, false, now), 'Delivered')
  assert.equal(nextChange([user, later], now), Date.parse('2026-10-05T10:30:00Z'))
  assert.equal(activityLine([user, later], {}, false, Date.parse('2026-10-05T10:31:00Z')), '')
  assert.equal(activityLine([user, { ...later, status: 'failed' }], {}, false, now), '')
  assert.equal(activityLine([user, { ...later, superseded_at: '2026-10-05T10:05:00Z' }], {}, false, now), '')
  assert.equal(lastUserMessage([user, later]), 'u')
})
