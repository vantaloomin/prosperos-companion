import assert from 'node:assert/strict'
import { test } from 'node:test'
import { emptyDefinition, listTexts } from '../../src/features/character/definition.ts'
import type { FormState } from '../../src/features/character/drafting.ts'
import { applied, fieldProposals, history, shownValue, splitForm, splitReply, undone, wantsSplit, type Turn } from '../../src/features/character/helper.ts'

const form = (change = {}): FormState => {
  const definition = { ...emptyDefinition('UTC'), name: 'Dana', skills: ['IVs'], ...change }
  return { definition, texts: listTexts(definition) }
}
let count = 0
const id = () => `p${++count}`

test('a long paste on an empty form is split; anything else goes to the conversation', () => {
  const long = 'x'.repeat(300)
  assert.equal(wantsSplit(form().definition, long), true)
  assert.equal(wantsSplit(form().definition, 'make her older'), false)
  assert.equal(wantsSplit(form({ identity: '34, a nurse' }).definition, long), false)
})

test('proposals skip fields the reply leaves as they are, and unknown fields', () => {
  const proposals = fieldProposals(form(), { name: 'Dana', skills: ['IVs', 'Parking'], relationship: 'romance' } as never, id)
  assert.deepEqual(proposals.map((item) => item.kind === 'field' && item.field), ['skills'])
})

test('applying a change keeps what it replaced, and Undo puts it back', () => {
  const [proposal] = fieldProposals(form(), { skills: ['IVs', 'Parking'], location: 'Baltimore' }, id)
  const done = applied(form(), proposal)
  assert.equal(done.state.texts.skills, 'IVs\nParking')
  assert.equal(done.proposal.status, 'applied')
  const back = undone(done.state, done.proposal)
  assert.equal(back.state.texts.skills, 'IVs')
  assert.equal(back.proposal.status, 'pending')
  const where = applied(form(), fieldProposals(form(), { location: 'Baltimore' }, id)[0])
  assert.equal(where.state.definition.location, 'Baltimore')
})

test('a split character fills the whole form but keeps the relationship the user chose', () => {
  const result = { definition: { ...emptyDefinition('America/New_York'), name: 'Dana Whitfield', relationship: 'friendship' as const, interests: ['crosswords'] }, filled_in: ['appearance' as const, 'schedule' as const], home_city: 'Baltimore' }
  const filled = splitForm(form({ relationship: 'mentor' }), result)
  assert.equal(filled.definition.relationship, 'mentor')
  assert.equal(filled.texts.interests, 'crosswords')
  assert.equal(splitReply(result), 'I split Dana Whitfield into the fields. Your text names Baltimore, so that is their home city. Your text did not cover appearance and weekly routine, so I filled those in; check them.')
  assert.equal(splitReply({ ...result, filled_in: [], home_city: '' }), 'I split Dana Whitfield into the fields. Everything came from your text.')
})

test('the weekly routine and lists read as plain text for comparing', () => {
  assert.equal(shownValue('schedule', [{ label: 'Asleep', kind: 'sleep', days: [0, 1, 2, 3, 4, 5, 6], start: '23:00', end: '07:00', themes: [] }, { label: 'Shift', kind: 'work', days: [0, 2], start: '19:00', end: '07:00', themes: [] }]),
    'Asleep: Every day, 23:00–07:00\nShift: Mon, Wed, 19:00–07:00')
  assert.equal(shownValue('flaws', ['Late', 'Blunt']), 'Late\nBlunt')
  assert.equal(shownValue('interests', ['tea', 'jazz']), 'tea, jazz')
})

test('the conversation sent back is the latest turns, cut to length', () => {
  const turns: Turn[] = Array.from({ length: 7 }, (_, index) => ({ id: `t${index}`, message: index === 6 ? 'y'.repeat(5000) : `ask ${index}`, reply: index === 3 ? '' : `reply ${index}`, proposals: [] }))
  const sent = history(turns)
  assert.equal(sent[0].content, 'ask 2')
  assert.equal(sent.filter((turn) => turn.role === 'assistant').length, 4)
  assert.equal(sent.at(-2)?.content.length, 4000)
})
