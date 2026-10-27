import assert from 'node:assert/strict'
import { test } from 'node:test'
import { canRetry, groupActivity, guestLine, guestMeters, latestLine, membersLine, namesText, shortTitle, shownMessages } from '../../src/features/groups/groupText.ts'
import type { Group, GroupMessage } from '../../src/types.ts'

const member = (label: string) => ({ companion_id: label, key: `companion:${label}`, name: `${label} Hart`, label, main: false, joined_at: '', sees_from: 1 })
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

test('a guest reads as who they are to the group, with their numbers only as hidden values', () => {
  const guest = { relation: "Mira's close friend", host_id: 'm', kept: false, regular: false, visits: 1, regular_after: 3, replies_left: 2, replies_each: 4 }
  const ada = { ...member('Ada'), companion_id: null, key: 'circle:t:1', guest }
  assert.equal(guestLine(ada), "Mira's close friend · guest")
  assert.equal(guestMeters(ada), 'visit 1 of 3 to stay · 2 of 4 replies left this conversation')
  assert.equal(guestLine({ ...ada, guest: { ...guest, regular: true } }), "Mira's close friend · regular")
  assert.equal(guestLine({ ...ada, guest: { ...guest, kept: true } }), "Mira's close friend · staying")
  assert.equal(guestMeters({ ...ada, guest: { ...guest, kept: true } }), '2 of 4 replies left this conversation')
  assert.equal(guestLine(member('Billy')), '')
})

test('the message box on a phone keeps the whole group name, or cuts it at a word', () => {
  assert.equal(shortTitle('Night out'), 'Night out')
  assert.equal(shortTitle('Billy and Sally'), 'Billy and Sally')
  assert.equal(shortTitle('Saturday brunch with the whole crew'), 'Saturday brunch…')
  assert.equal(shortTitle('Spock, Leonard McCoy and James Kirk'), 'Spock, Leonard McCoy…')
  assert.equal(shortTitle('Mira, Sam and Leonard'), 'Mira, Sam…')
  assert.equal(shortTitle('Drinks with the team after work'), 'Drinks with the team…')
  assert.equal(shortTitle('Coffee with Sam and the rest'), 'Coffee with Sam…')
  assert.equal(shortTitle('Supercalifragilisticexpialidocious'), 'Supercalifragilistic…')
})
