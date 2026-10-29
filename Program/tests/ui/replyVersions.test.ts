import assert from 'node:assert/strict'
import { test } from 'node:test'
import { applyChosen, applyFinished, defaultAttempt, defaultVersion, followUpAfter, groupTurns, leadVersions } from '../../src/features/conversation/turns.ts'
import type { Message } from '../../src/types.ts'

function message(id: string, seq: number, extra: Partial<Message> = {}): Message {
  return { id, seq, timeline_id: 't', role: 'user', text: id, reply_to: null, status: 'complete', active: true, redacted: false,
    error: null, character_version_id: null, created_at: '2026-10-05T12:00:00Z', completed_at: null, ...extra }
}
const reply = (id: string, seq: number, to: string, extra: Partial<Message> = {}) => message(id, seq, { role: 'companion', reply_to: to, ...extra })
const later = (id: string, seq: number, extra: Partial<Message> = {}) => message(id, seq, { role: 'companion', held_line: 'brb', ...extra })

test('the version paged back to stays shown on the newest message and once the user writes again', () => {
  const rerolled = [message('u1', 1), reply('a', 2, 'u1', { active: false }), reply('b', 3, 'u1')]
  const chosen = applyChosen(rerolled, rerolled[1])
  assert.deepEqual(chosen.map((item) => [item.id, item.active]), [['u1', true], ['a', true], ['b', false]])
  assert.equal(defaultAttempt(groupTurns(chosen)[0], true)?.id, 'a')
  const answered = [...chosen, message('u2', 4), reply('c', 5, 'u2')]
  assert.equal(defaultAttempt(groupTurns(answered)[0])?.id, 'a')
})

test('on the newest message a reply being written or one that failed still shows over the chosen one', () => {
  const writing = [message('u1', 1), reply('a', 2, 'u1'), reply('b', 3, 'u1', { active: false, status: 'streaming' })]
  assert.equal(defaultAttempt(groupTurns(writing)[0], true)?.id, 'b')
  assert.equal(defaultAttempt(groupTurns(writing)[0])?.id, 'a')
})

test('the full reply after a holding text pages through its versions', () => {
  const messages = [message('u1', 1), reply('note', 2, 'u1'), later('full', 3, { active: false }), later('v2', 4, { version_of: 'full' })]
  const turns = groupTurns(messages)
  const last = turns.at(-1)!
  assert.deepEqual(last.leads.map((lead) => lead.id), ['full'])
  assert.deepEqual(leadVersions(last, last.leads[0]).map((version) => version.id), ['full', 'v2'])
  assert.equal(defaultVersion(leadVersions(last, last.leads[0]), true)?.id, 'v2')
  assert.equal(followUpAfter(turns)?.id, 'full')
  const chosen = applyChosen(messages, messages[2])
  assert.deepEqual(chosen.map((item) => [item.id, item.active]), [['u1', true], ['note', true], ['full', true], ['v2', false]])
})

test('a finished version of the full reply leaves the holding text and other messages alone', () => {
  const messages = [message('u1', 1), reply('note', 2, 'u1'), later('full', 3), message('o', 4, { role: 'companion' })]
  const done = applyFinished([...messages, later('v2', 5, { version_of: 'full', status: 'streaming', active: false })],
    later('v2', 5, { version_of: 'full' }))
  assert.deepEqual(done.map((item) => [item.id, item.active]), [['u1', true], ['note', true], ['full', false], ['o', true], ['v2', true]])
})

test('no follow-up when the newest turn is the user message', () => {
  assert.equal(followUpAfter(groupTurns([message('u1', 1), reply('a', 2, 'u1')])), undefined)
})
