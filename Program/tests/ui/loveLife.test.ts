import { test } from 'node:test'
import assert from 'node:assert/strict'
import { appLove, loveChange, loveSuggestions, loveValues } from '../../src/features/today/loveText.ts'
import type { CircleLove } from '../../src/types.ts'

const info = (change: Partial<CircleLove> = {}): CircleLove => ({ state: 'seeing', partner: 'Liss', set: false, editable: true, people: [], ...change })

test('the app pick says what the app has now, by first name', () => {
  assert.equal(appLove(info()), 'Let the app pick (Seeing Liss)')
  assert.equal(appLove(info({ state: 'single', partner: null })), 'Let the app pick (Single)')
  assert.equal(appLove(info({ state: 'married', partner: 'Ren' })), 'Let the app pick (Married to Ren)')
  assert.equal(appLove(info({ state: 'divorced', partner: null })), 'Let the app pick (Divorced)')
  assert.equal(appLove(info({ set: true })), 'Let the app pick')
})

test('the form starts on the user pick, or the app pick', () => {
  assert.deepEqual(loveValues(info()), { love: '', partner: '' })
  assert.deepEqual(loveValues(info({ set: true, state: 'engaged', partner: 'Ren' })), { love: 'engaged', partner: 'Ren' })
  assert.deepEqual(loveValues(info({ set: true, state: 'single', partner: null })), { love: 'single', partner: '' })
})

test('only a change is sent, and who with only when it is on', () => {
  const app = { love: '', partner: '' } as const
  assert.deepEqual(loveChange(app, app), {})
  assert.deepEqual(loveChange(app, { love: 'married', partner: ' Ren Ito ' }), { love: 'married', partner_name: 'Ren Ito' })
  assert.deepEqual(loveChange(app, { love: 'seeing', partner: '' }), { love: 'seeing' })
  assert.deepEqual(loveChange(app, { love: 'single', partner: 'Ren' }), { love: 'single' })
  assert.deepEqual(loveChange({ love: 'married', partner: 'Ren' }, { love: '', partner: 'Ren' }), { love: '' })
})

test('who with shows where each one stands', () => {
  const found = loveSuggestions(info({ people: [{ id: 'a', name: 'Dana', stands: 'married to Kaito' }, { id: 'b', name: 'Mo', stands: null }] }))
  assert.deepEqual(found.options, ['Dana', 'Mo'])
  assert.deepEqual(found.notes, { Dana: 'married to Kaito' })
})
