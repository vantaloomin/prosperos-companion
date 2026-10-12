import assert from 'node:assert/strict'
import { test } from 'node:test'
import { importedText, type ChatImportResult } from '../../src/features/character/chatImportText.ts'
import { endsOlderHistory, groupTurns, latestUser } from '../../src/features/conversation/turns.ts'
import type { Message } from '../../src/types.ts'

const result: ChatImportResult = { id: 'i', filename: 'chat.jsonl', format: 'sillytavern', messages: 312, skipped: 0, memories: 14, dated: true,
  first_at: '2024-03-01T14:05:00+00:00', last_at: '2024-05-09T10:00:00+00:00', automatic_memory: true }

function message(id: string, seq: number, extra: Partial<Message> = {}): Message {
  return { id, seq, timeline_id: 't', role: 'user', text: id, reply_to: null, status: 'complete', active: true, redacted: false,
    error: null, character_version_id: null, created_at: '2026-10-05T12:00:00Z', completed_at: null, ...extra }
}

test('an import says what came in, when it was said and how many memories were found', () => {
  assert.equal(importedText(result), '312 messages from 2024-03-01 to 2024-05-09 came in as older history; 14 memories found.')
  assert.equal(importedText({ ...result, messages: 1, memories: 1, last_at: result.first_at }), '1 message from 2024-03-01 came in as older history; 1 memory found.')
  assert.equal(importedText({ ...result, messages: 1200, dated: false, memories: 0, skipped: 2 }),
    "1,200 messages (the file has no dates, so they sit just before the rest of the chat) came in as older history; 0 memories found. 2 system, narrator, empty or other characters' lines were left out.")
  assert.match(importedText({ ...result, automatic_memory: false }), /older history\. Remembering things automatically is off/)
})

test('older history is never the latest message and its end is marked', () => {
  const imported = { import_id: 'i' }
  const turns = groupTurns([message('o1', -3, { ...imported, role: 'companion' }), message('u1', -2, imported),
    message('r1', -1, { ...imported, role: 'companion', reply_to: 'u1' })])
  assert.equal(latestUser(turns), undefined)
  assert.deepEqual(turns.map((_turn, index) => endsOlderHistory(turns, index)), [true])
  const later = groupTurns([message('u1', -2, imported), message('u2', 1), message('r2', 2, { role: 'companion', reply_to: 'u2' })])
  assert.equal(latestUser(later), 'u2')
  assert.deepEqual(later.map((_turn, index) => endsOlderHistory(later, index)), [true, false])
})
