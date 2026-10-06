import assert from 'node:assert/strict'
import { test } from 'node:test'
import { budgetShare, receiptRows } from '../../src/features/memories/receiptRows.ts'
import type { ContextReceipt, Memory } from '../../src/types.ts'

const memory = (id: string, subject: string) => ({ id, subject }) as Memory

test('rows follow the builder order, name memories and count what was left out', () => {
  const receipt: ContextReceipt = {
    budget_tokens: 1000, estimated_tokens: 250,
    included: { profile: ['m1', 'm2'], character: ['v1'], conversation: ['a', 'b', 'c'], new_section: ['x'] },
    omitted: { conversation: ['old'], recalled: ['m3'] },
  }
  const rows = receiptRows(receipt, [memory('m1', 'Job'), memory('m2', 'Sister')], 'Mira')
  assert.deepEqual(rows.map((row) => row.key), ['character', 'conversation', 'profile', 'recalled', 'new_section'])
  assert.equal(rows[0].label, "Mira's character")
  assert.deepEqual(rows[1], { key: 'conversation', label: 'Recent messages', included: 3, omitted: 1, detail: '3 messages' })
  assert.equal(rows[0].detail, 'Included')
  assert.equal(rows[2].detail, 'Job, Sister')
  assert.equal(rows[3].detail, 'None included')
  assert.equal(rows[4].label, 'new section')
})

test('budget share is a capped percentage', () => {
  assert.equal(budgetShare({ budget_tokens: 1000, estimated_tokens: 250, included: {}, omitted: {} }), 25)
  assert.equal(budgetShare({ budget_tokens: 100, estimated_tokens: 250, included: {}, omitted: {} }), 100)
})
