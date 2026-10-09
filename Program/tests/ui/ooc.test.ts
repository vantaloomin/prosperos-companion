import assert from 'node:assert/strict'
import { test } from 'node:test'
import { DEFAULT_OOC_MARKERS, splitOoc } from '../../src/features/conversation/ooc.ts'

test('a message starting with OOC: goes to the helper whole', () => {
  assert.deepEqual(splitOoc('ooc: why did she say that?', DEFAULT_OOC_MARKERS), { story: '', aside: 'why did she say that?' })
  assert.deepEqual(splitOoc('  OOC:fix her birthday', DEFAULT_OOC_MARKERS), { story: '', aside: 'fix her birthday' })
})

test('an aside in double parentheses is split off', () => {
  assert.deepEqual(splitOoc('See you tomorrow ((brb, dinner))', DEFAULT_OOC_MARKERS), { story: 'See you tomorrow', aside: 'brb, dinner' })
  assert.deepEqual(splitOoc('((one)) Hi there ((two)).', DEFAULT_OOC_MARKERS), { story: 'Hi there.', aside: 'one\ntwo' })
  assert.deepEqual(splitOoc('((only this))', DEFAULT_OOC_MARKERS), { story: '', aside: 'only this' })
})

test('an unclosed aside runs to the end', () => {
  assert.deepEqual(splitOoc('Goodnight ((also, change her job', DEFAULT_OOC_MARKERS), { story: 'Goodnight', aside: 'also, change her job' })
})

test('a message without markers is left alone', () => {
  assert.deepEqual(splitOoc('Hello (just one paren) there', DEFAULT_OOC_MARKERS), { story: 'Hello (just one paren) there', aside: '' })
  assert.deepEqual(splitOoc('Remember the OOC: thing?', DEFAULT_OOC_MARKERS), { story: 'Remember the OOC: thing?', aside: '' })
  assert.deepEqual(splitOoc('((brb))', []), { story: '((brb))', aside: '' })
})

test('the user can add their own markers', () => {
  const markers = [...DEFAULT_OOC_MARKERS, { open: '[[', close: ']]' }, { open: '//', close: '' }]
  assert.deepEqual(splitOoc('Sure [[is she too clingy?]]', markers), { story: 'Sure', aside: 'is she too clingy?' })
  assert.deepEqual(splitOoc('// note to self', markers), { story: '', aside: 'note to self' })
})
