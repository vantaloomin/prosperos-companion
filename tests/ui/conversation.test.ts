import assert from 'node:assert/strict'
import { test } from 'node:test'
import { applyFinished, defaultAttempt, groupTurns, liveFor, mergeMessages, replyAnnouncement, streamingIds } from '../../src/features/conversation/turns.ts'
import { editDraft, newDraft, readDraft, writeDraft } from '../../src/features/conversation/draft.ts'
import type { Message } from '../../src/types.ts'

function message(id: string, seq: number, extra: Partial<Message> = {}): Message {
  return { id, seq, timeline_id: 't', role: 'user', text: id, reply_to: null, status: 'complete', active: true, redacted: false,
    error: null, character_version_id: null, created_at: '2026-10-05T12:00:00Z', completed_at: null, ...extra }
}
const reply = (id: string, seq: number, to: string, extra: Partial<Message> = {}) => message(id, seq, { role: 'companion', reply_to: to, ...extra })

test('turns pair user messages with their attempts and skip orphans', () => {
  const turns = groupTurns([reply('r0', 1, 'missing'), message('u1', 2), reply('r1', 3, 'u1'), message('u2', 4)])
  assert.deepEqual(turns.map((turn) => [turn.user.id, turn.attempts.map((attempt) => attempt.id)]), [['u1', ['r1']], ['u2', []]])
})

test('the active complete reply is shown, otherwise the latest attempt', () => {
  const [withActive] = groupTurns([message('u', 1), reply('a', 2, 'u'), reply('b', 3, 'u', { active: false, status: 'failed' })])
  assert.equal(defaultAttempt(withActive)?.id, 'a')
  assert.equal(defaultAttempt(withActive, true)?.id, 'b')
  const [failed] = groupTurns([message('u', 1), reply('a', 2, 'u', { active: false, status: 'cancelled' }), reply('b', 3, 'u', { active: false, status: 'failed' })])
  assert.equal(defaultAttempt(failed)?.id, 'b')
})

test('streaming attempts are found for reattaching after a reload', () => {
  assert.deepEqual(streamingIds([message('u', 1), reply('r', 2, 'u', { status: 'streaming', active: false })]), ['r'])
})

test('a finished active reply deactivates the earlier one', () => {
  const current = [message('u', 1), reply('a', 2, 'u'), reply('b', 3, 'u', { status: 'streaming', active: false })]
  const next = applyFinished(current, reply('b', 3, 'u', { text: 'done' }))
  assert.deepEqual(next.map((item) => [item.id, item.active]), [['u', true], ['a', false], ['b', true]])
})

test('merging replaces by id and keeps order', () => {
  assert.deepEqual(mergeMessages([message('b', 2)], [message('a', 1), message('b', 2, { text: 'new' })]).map((item) => item.text), ['a', 'new'])
})

test('editing the draft text gives it a new client id; unchanged text keeps it', () => {
  let counter = 0
  const makeId = () => `id-${++counter}`
  const draft = newDraft('Hi', makeId)
  assert.equal(editDraft(draft, 'Hi', makeId), draft)
  assert.equal(editDraft(draft, 'Hi there', makeId).clientId, 'id-2')
})

test('drafts survive storage round trips and damaged slots start empty', () => {
  const values = new Map<string, string>()
  const storage = { getItem: (key: string) => values.get(key) ?? null, setItem: (key: string, value: string) => { values.set(key, value) }, removeItem: (key: string) => { values.delete(key) } }
  writeDraft(storage, { text: 'Unsent', clientId: 'c1' })
  assert.deepEqual(readDraft(storage), { text: 'Unsent', clientId: 'c1' })
  values.set('companion:draft', '{bad')
  assert.equal(readDraft(storage).text, '')
  writeDraft(storage, { text: '', clientId: 'c2' })
  assert.equal(values.size, 0)
})

test('a finished reply is announced with the words shown under it, without repeating that it was stopped', () => {
  assert.equal(replyAnnouncement('Mira', message('r', 2, { role: 'companion', status: 'complete' })), 'Mira replied.')
  assert.equal(replyAnnouncement('Mira', message('r', 2, { role: 'companion', status: 'cancelled', error: 'Stopped.' })), 'You stopped this reply.')
  assert.equal(replyAnnouncement('Mira', message('r', 2, { role: 'companion', status: 'failed', error: 'The model timed out.' })), 'This reply failed. The model timed out.')
})

test('only the turn being streamed sees the live text; the others keep the same empty map', () => {
  const [quiet, streaming] = groupTurns([message('u1', 1), reply('r1', 2, 'u1'), message('u2', 3), reply('r2', 4, 'u2')])
  const live = { r2: 'Hello' }
  assert.equal(liveFor(streaming, live), live)
  assert.equal(liveFor(quiet, live), liveFor(quiet, { r2: 'Hello again' }))
  assert.deepEqual(liveFor(quiet, live), {})
})

test('regrouping keeps unchanged turns identical so they skip re-rendering', () => {
  const messages = [message('u1', 1), reply('r1', 2, 'u1'), message('u2', 3), reply('r2', 4, 'u2', { status: 'streaming' })]
  const before = groupTurns(messages)
  const after = groupTurns(applyFinished(messages, reply('r2', 4, 'u2', { status: 'complete', active: true })))
  assert.equal(after[0], before[0])
  assert.notEqual(after[1], before[1])
  assert.equal(after[1].attempts[0].status, 'complete')
})
