import assert from 'node:assert/strict'
import { test } from 'node:test'
import { addedLine, appliesText, dateParts, happenedAt, correction, dayInput, deletePreviewText, earlierVersions, followUp, groupMemories, groupPeople, personLine, rememberedText, statusLabels, suggestionReason, titleFrom } from '../../src/features/memories/memoryGroups.ts'
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

test('finished plans fold away under the open ones, newest first', () => {
  const plan = (id: string, plan_status: Memory['plan_status'], updated_at = '2026-10-05T12:00:00Z') => memory(id, { layer: 'plan', plan_status, updated_at })
  const [group] = groupMemories([plan('open', 'agreed'), plan('done', 'completed', '2026-10-02T00:00:00Z'), plan('off', 'cancelled', '2026-10-04T00:00:00Z')])
  assert.deepEqual(group.current.map((item) => item.id), ['open'])
  assert.deepEqual(group.finished.map((item) => item.id), ['off', 'done'])
  assert.deepEqual(groupMemories([plan('done', 'completed')]).map((item) => item.finished.length), [1])
})

test('a plan that closed on its own says so and asks to be put right', () => {
  const now = new Date('2026-10-05T12:00:00Z')
  const settled = memory('trip', { layer: 'plan', plan_status: 'completed', settled_from: 'agreed', applies_from: '2026-10-01T00:00:00Z' })
  assert.equal(followUp(settled, now), 'settled')
  assert.deepEqual(statusLabels(settled), ['Assumed done'])
  assert.equal(followUp({ ...settled, plan_status: 'cancelled' }, now), null)
})

test('shared moments list newest first by when they happened, pinned ones in their place', () => {
  const moment = (id: string, day: string, extra: Partial<Memory> = {}) => memory(id, { layer: 'shared_experience', stated_at: `${day}T23:00:00Z`, ...extra })
  const groups = groupMemories([moment('wedding', '2026-06-12', { pinned: true }), moment('march', '2026-03-07'), moment('may', '2026-05-16', { pinned: true }),
    moment('trip', '2026-01-01', { applies_from: '2026-08-07T00:00:00Z' })])
  assert.deepEqual(groups[0].current.map((item) => item.id), ['trip', 'wedding', 'may', 'march'])
})

test('only a memory you added yourself says so; one saved automatically leaves it to its badge', () => {
  assert.equal(addedLine(memory('mine')), 'Added by you directly.')
  assert.equal(addedLine(memory('visit', { origin: 'automatic' })), null)
  assert.equal(addedLine(memory('said', { source_message_ids: ['m1'] })), null)
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
  assert.deepEqual(statusLabels(memory('chicago', { status: 'superseded', retracted: true })), ['You said this was wrong'])
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
  assert.match(suggestionReason('correction', ['Chicago'], false, true), /^You said “Chicago” isn't right\. Remember drops it/)
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

test('a memory saved without a title is named by its first words', () => {
  assert.equal(titleFrom('  QonCat  '), 'QonCat')
  assert.equal(titleFrom('Likes to be called Q by close friends only'), 'Likes to be called Q by…')
})

test('a memory with no end date applies from its start, not "to …"', () => {
  const show = (value: string) => value
  assert.equal(appliesText('Oct 6', null, show), 'Applies from Oct 6')
  assert.equal(appliesText(null, 'Oct 9', show), 'Applies until Oct 9')
  assert.equal(appliesText('Oct 6', 'Oct 9', show), 'Applies Oct 6 to Oct 9')
})

test('a moment with only a start happened then, and a hand-written one is dated the chosen day or today', () => {
  const show = (value: string) => value
  const met = memory('met', { layer: 'shared_experience', applies_from: 'May 3', stated_at: 'Oct 25' })
  assert.deepEqual(dateParts(met, show), ['Happened May 3 · said Oct 25'])
  assert.deepEqual(dateParts({ ...met, applies_until: 'May 9' }, show), ['Said Oct 25', 'Applies May 3 to May 9'])
  assert.deepEqual(dateParts({ ...met, layer: 'user_fact' }, show), ['Said Oct 25', 'Applies from May 3'])
  assert.equal(happenedAt(''), null)
  assert.equal(happenedAt('2026-05-03'), new Date('2026-05-03T00:00').toISOString())
})
