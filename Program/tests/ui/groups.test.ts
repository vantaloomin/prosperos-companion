import assert from 'node:assert/strict'
import { test } from 'node:test'
import { canRetry, groupActivity, latestLine, membersLine, namesText, shownMessages } from '../../src/features/groups/groupText.ts'
import type { Group, GroupMessage } from '../../src/types.ts'

const member = (label: string) => ({ companion_id: label, name: `${label} Hart`, label, main: false, joined_at: '', sees_from: 1 })
const group: Group = { id: 'g', name: '', title: 'Billy and Sally', reply_cap: 2, created_at: '', updated_at: '', members: [member('Billy'), member('Sally')] }
const message = (id: string, kind: GroupMessage['kind'], extra: Partial<GroupMessage> = {}): GroupMessage =>
  ({ id, seq: 1, kind, companion_id: null, name: kind === 'user' ? 'User' : 'Billy', text: 'hi', status: 'complete', error: null, reply_to: null, created_at: '', ...extra })

test('names read as a sentence', () => {
  assert.equal(namesText(['Billy']), 'Billy')
  assert.equal(namesText(['Billy', 'Sally', 'Mira']), 'Billy, Sally and Mira')
  assert.equal(membersLine(group), 'You, Billy and Sally')
  assert.equal(membersLine({ ...group, members: [] }), 'Only you')
})

test('the latest line names who wrote it', () => {
  assert.equal(latestLine({ ...group, latest: message('1', 'companion', { text: 'see you' }) }), 'Billy: see you')
  assert.equal(latestLine({ ...group, latest: message('1', 'user') }), 'You: hi')
  assert.equal(latestLine({ ...group, latest: message('1', 'app', { text: 'You added Sally.' }) }), 'You added Sally.')
})

test('the activity line describes the app, never who is typing', () => {
  assert.equal(groupActivity({ busy: false, phase: null }, true), 'Sending…')
  assert.equal(groupActivity({ busy: true, phase: 'writing' }, false), 'Writing a reply…')
  assert.equal(groupActivity({ busy: true, phase: 'preparing' }, false), 'Getting replies ready…')
  assert.equal(groupActivity({ busy: false, phase: null }, false), '')
})

test('a reply shows once its first words arrive', () => {
  const writing = message('2', 'companion', { status: 'streaming', text: '' })
  assert.deepEqual(shownMessages([message('1', 'user'), writing], {}).map((item) => item.id), ['1'])
  assert.equal(shownMessages([writing], { 2: 'Hey' })[0].text, 'Hey')
})

test('a failed reply can be tried again once the round is over', () => {
  const user = message('1', 'user')
  const failed = message('2', 'companion', { status: 'failed', reply_to: '1' })
  assert.equal(canRetry({ busy: false, messages: [user, failed] }), true)
  assert.equal(canRetry({ busy: true, messages: [user, failed] }), false)
  assert.equal(canRetry({ busy: false, messages: [user, { ...failed, status: 'complete' }] }), false)
})
