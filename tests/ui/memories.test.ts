import assert from 'node:assert/strict'
import { test } from 'node:test'
import { earlierVersions, groupMemories, statusLabels } from '../../src/features/memories/memories.ts'
import type { Memory } from '../../src/types.ts'

function memory(id: string, extra: Partial<Memory> = {}): Memory {
  return { id, layer: 'user_fact', subject: id, value: 'v', reality: 'real', authority: 'stated', status: 'active', boundary: false, pinned: false,
    sensitive: false, plan_status: null, stated_at: '2026-10-05T12:00:00Z', applies_from: null, applies_until: null, revision: 1,
    supersedes_id: null, source_message_ids: [], updated_at: '2026-10-05T12:00:00Z', ...extra }
}

test('memories group by layer in display order with pinned first and history apart', () => {
  const groups = groupMemories([memory('b'), memory('a'), memory('z', { pinned: true }), memory('old', { status: 'superseded' }), memory('trip', { layer: 'plan' })])
  assert.deepEqual(groups.map((group) => group.layer), ['user_fact', 'plan'])
  assert.deepEqual(groups[0].current.map((item) => item.id), ['z', 'a', 'b'])
  assert.deepEqual(groups[0].history.map((item) => item.id), ['old'])
})

test('earlier versions follow supersession links newest first', () => {
  const all = [memory('v1', { status: 'superseded' }), memory('v2', { status: 'superseded', supersedes_id: 'v1' }), memory('v3', { supersedes_id: 'v2' })]
  assert.deepEqual(earlierVersions(all[2], all).map((item) => item.id), ['v2', 'v1'])
})

test('labels describe state in words', () => {
  assert.deepEqual(statusLabels(memory('m', { boundary: true, status: 'excluded', authority: 'tentative', plan_status: 'agreed' })),
    ['Boundary', 'Not used in conversation', 'Unconfirmed guess', 'Agreed'])
})
