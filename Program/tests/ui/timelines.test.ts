import assert from 'node:assert/strict'
import { test } from 'node:test'
import { forkNote, timelineSummary, waitingDraft } from '../../src/features/conversation/timelineText.ts'
import type { Timeline } from '../../src/types.ts'

function timeline(id: string, extra: Partial<Timeline> = {}): Timeline {
  return { id, label: id, status: 'frozen', active: false, parent_id: null, fork_message_id: null, forked_at: null,
    created_at: '2026-10-05T12:00:00Z', activated_at: null, frozen_at: null, draft: null, messages: 2,
    last_message_at: null, latest_text: '', ...extra }
}

test('the summary says which timeline is current and which edit has not been started', () => {
  assert.equal(timelineSummary(timeline('a', { active: true, status: 'active', messages: 1 })), 'Current · 1 message')
  assert.match(timelineSummary(timeline('b', { parent_id: 'a', draft: 'Hi' })), /^Not started yet · 2 messages, with your edit waiting$/)
  assert.match(timelineSummary(timeline('c', { activated_at: '2026-10-05T12:00:00Z', frozen_at: '2026-10-06T12:00:00Z' })), /^Set aside since /)
})

test('a fork names the timeline it branched from', () => {
  const original = timeline('a', { label: 'Original' })
  const fork = timeline('b', { parent_id: 'a', forked_at: '2026-10-05T12:00:00Z' })
  assert.match(forkNote(fork, [original, fork]) ?? '', /^Branched from Original at a message from /)
  assert.equal(forkNote(original, [original, fork]), null)
})

test('the edited words go into the message box only when it is empty and the timeline is current', () => {
  const current = timeline('b', { active: true, status: 'active', draft: 'I went to the coast.' })
  assert.equal(waitingDraft(current, ''), 'I went to the coast.')
  assert.equal(waitingDraft(current, 'Something I was typing'), null)
  assert.equal(waitingDraft({ ...current, active: false }, ''), null)
  assert.equal(waitingDraft(undefined, ''), null)
})
