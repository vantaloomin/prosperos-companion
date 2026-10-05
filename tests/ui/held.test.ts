import assert from 'node:assert/strict'
import { test } from 'node:test'
import { heldNote, isHeld, releaseHeld } from '../../src/features/conversation/held.ts'
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

test('the note says busy or asleep', () => {
  assert.match(heldNote(message({ held_until: '2026-10-05T10:30:00Z', held_line: 'brb' }), 'Mira'), /^Mira is busy\. Their full reply shows at /)
  assert.match(heldNote(message({ held_until: '2026-10-05T07:00:00Z', held_line: null }), 'Mira'), /^Mira is asleep\./)
})

test('writing again shows replies held before it', () => {
  const released = releaseHeld([message({ held_until: '2099-01-01T00:00:00Z' }), message({ id: 'n', seq: 5, held_until: '2099-01-01T00:00:00Z' })], 4)
  assert.deepEqual(released.map((item) => item.held_until), [null, '2099-01-01T00:00:00Z'])
})
