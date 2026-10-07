import assert from 'node:assert/strict'
import { test } from 'node:test'
import { correction, dayInput, deletePreviewText, earlierVersions, followUp, groupMemories, groupPeople, personLine, rememberedText, statusLabels, suggestionReason } from '../../src/features/memories/memoryGroups.ts'
import type { Memory, Person } from '../../src/types.ts'

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

test('history, uncertainty and automatic saving are labelled', () => {
  assert.deepEqual(statusLabels(memory('chicago', { current: false, origin: 'automatic', dates_uncertain: true })),
    ['No longer current', 'Dates uncertain', 'Saved automatically'])
  assert.deepEqual(statusLabels(memory('plan', { layer: 'plan', plan_status: 'agreed', current: false })), ['Agreed'])
})

test('remember this describes what was kept', () => {
  assert.equal(rememberedText('Mira', [{ subject: 'Home city', value: 'Chicago' }]), 'Mira will remember this: Home city: Chicago.')
  assert.equal(suggestionReason('sensitive'), 'Sensitive details are only kept when you say so.')
})

test('the delete preview names what goes and what stays', () => {
  const preview = { memory_ids: ['a'], source_message_ids: ['m1', 'm2'], other_memories: [{ id: 'b', subject: "Sister's city" }], summaries_with_sources: 1, kept: '' }
  assert.deepEqual(deletePreviewText(preview, false), [])
  assert.deepEqual(deletePreviewText(preview, true), ['2 messages will show as deleted in your conversation.',
    '1 conversation summary quoting them will be removed.', "Also from those messages, and kept: Sister's city."])
})

test('a past open plan asks whether it happened; an unclear date asks for the date', () => {
  const now = new Date('2026-10-05T12:00:00Z')
  assert.equal(followUp(memory('trip', { layer: 'plan', plan_status: 'agreed', applies_from: '2026-10-01T00:00:00Z' }), now), 'outcome')
  assert.equal(followUp(memory('trip', { layer: 'plan', plan_status: 'completed', applies_from: '2026-10-01T00:00:00Z' }), now), null)
  assert.equal(followUp(memory('trip', { layer: 'plan', plan_status: 'agreed', applies_from: '2026-11-01T00:00:00Z', dates_uncertain: true }), now), 'date')
  assert.equal(followUp(memory('trip', { status: 'excluded', dates_uncertain: true }), now), null)
})

test('a correction sends only what changed, and resends uncertain dates to confirm them', () => {
  const plan = memory('trip', { layer: 'plan', value: 'Lisbon', plan_status: 'agreed', applies_from: new Date('2026-11-01T00:00').toISOString() })
  const draft = { value: 'Lisbon', plan_status: 'agreed' as const, from: dayInput(plan.applies_from), until: '' }
  assert.equal(draft.from, '2026-11-01')
  assert.equal(correction(plan, draft), null)
  assert.deepEqual(correction(plan, { ...draft, plan_status: 'completed' }), { value: 'Lisbon', plan_status: 'completed', applies_from: undefined, applies_until: undefined })
  const confirmed = correction({ ...plan, dates_uncertain: true }, draft)
  assert.equal(confirmed?.applies_from, plan.applies_from)
  assert.equal(correction(plan, { ...draft, value: '  ' }), null)
})

test('a conflicting suggestion names the value it would replace', () => {
  assert.match(suggestionReason('conflict', ['Chicago']), /different from “Chicago”, and you didn't say it changed/)
  assert.match(suggestionReason('conflict'), /^This is different, and/)
})

test('a correction suggestion names the memory it corrects or ends', () => {
  assert.match(suggestionReason('correction', ['she loves gardening']), /^This corrects “she loves gardening”\. Remember replaces it/)
  assert.match(suggestionReason('correction', ['Chicago'], true), /^You said “Chicago” is no longer true\./)
})

test('a memory from another timeline is marked', () => {
  assert.ok(statusLabels(memory('m', { in_timeline: false })).includes('Another timeline'))
  assert.ok(!statusLabels(memory('m', { in_timeline: true })).includes('Another timeline'))
})

function person(id: string, extra: Partial<Person> = {}): Person {
  return { id, name: null, relation: null, label: id, last_mentioned_at: null, created_at: '2026-10-05T12:00:00Z', memory_ids: [], ...extra }
}

test('what you said about people is grouped by person, who they are first, and not under About you', () => {
  const all = [memory('mine'), memory('jo-likes', { subject: 'Jo: Likes', person_id: 'jo', subject_key: 'person.jo.likes' }),
    memory('jo-who', { subject: 'Sister', person_id: 'jo', subject_key: 'person.jo.who' }),
    memory('jo-old', { subject: 'Jo: Work', person_id: 'jo', status: 'superseded' })]
  assert.deepEqual(groupMemories(all)[0].current.map((item) => item.id), ['mine'])
  const [jo, ...rest] = groupPeople([person('jo', { name: 'Jo', relation: 'sister' }), person('nobody')], all)
  assert.deepEqual(jo.current.map((item) => item.id), ['jo-who', 'jo-likes'])
  assert.equal(rest.length, 0, 'someone with nothing current left is not listed')
})

test('a person is described by relation, or by what is still unknown', () => {
  assert.equal(personLine(person('a', { name: 'Jo', relation: 'sister' })), 'Your sister')
  assert.equal(personLine(person('b', { relation: 'mum' })), 'Name not known yet')
  assert.equal(personLine(person('c', { name: 'Sam' })), 'Relation not known yet')
})
