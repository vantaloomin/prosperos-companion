import assert from 'node:assert/strict'
import { test } from 'node:test'
import { emptyDefinition, listTexts } from '../../src/features/character/definition.ts'
import type { FormState } from '../../src/features/character/drafting.ts'
import { shownValue, splitForm, splitReply, wantsSplit } from '../../src/features/character/helper.ts'
import { history, proposals, title, effect, type Turn } from '../../src/features/sidecar/proposals.ts'

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

test('field proposals skip fields that already say exactly that, and read their value before', () => {
  const found = proposals([{ kind: 'field', field: 'name', value: 'Dana' }, { kind: 'field', field: 'skills', value: ['IVs', 'Parking'] }], form(), null, id)
  assert.equal(found.length, 1)
  assert.equal(found[0].before, 'IVs')
  assert.equal(title(found[0], 'Dana'), 'Skills')
  assert.equal(effect(found[0], true), 'Changes the form; nothing is saved until you save it.')
  assert.equal(effect(found[0], false), 'Saves a new character version.')
  const saved = proposals([{ kind: 'field', field: 'voice', value: 'Short.' }], null, { ...emptyDefinition(), voice: 'Long.' }, id)
  assert.equal(saved[0].before, 'Long.')
})

test('reply and memory proposals keep what they replace', () => {
  const [reply, memory, forget] = proposals([
    { kind: 'reply', message_id: 'r1', before: 'I adore jazz.', text: 'Jazz, mostly.', created_at: 'not a date' },
    { kind: 'memory', memory_id: 'k1', revision: 1, layer: 'user_fact', subject: 'job', before: 'Bakery', value: 'Florist' },
    { kind: 'forget_memory', memory_id: 'k2', layer: 'user_fact', subject: 'pet', before: 'Has a cat' }], null, null, id)
  assert.equal(reply.before, 'I adore jazz.')
  assert.equal(title(reply, 'Mira'), "Mira's reply")
  assert.equal(title(memory, 'Mira'), 'Memory: job')
  assert.equal(effect(forget, false), 'Keeps it in Memories but stops using it.')
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

test('connecting a model is the first step, and creating waits on it', async () => {
  const { welcomeSteps } = await import('../../src/features/character/welcomeSteps.ts')
  const [model, create] = welcomeSteps(null)
  assert.equal(model.action, 'Set up a model')
  assert.equal(model.primary, true)
  assert.equal(create.primary, false)
  assert.equal(create.action, 'Create without a model for now')
  const connected = welcomeSteps({ model: 'gemma', provider_name: 'OpenRouter' } as never)
  assert.equal(connected[0].done, true)
  assert.equal(connected[1].action, 'Create your companion')
  assert.equal(connected[1].primary, true)
  assert.equal(welcomeSteps(undefined)[0].action, '')
})
