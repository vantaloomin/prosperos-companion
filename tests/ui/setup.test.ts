import assert from 'node:assert/strict'
import { test } from 'node:test'
import { setupSteps } from '../../src/features/conversation/setup.ts'
import type { Companion, Connection } from '../../src/types.ts'

const companion = (definition: object) => ({ version: { name: 'Mira', definition: { home_city: '', schedule: [], ...definition } } }) as unknown as Companion

test('a new companion still needs a model and, optionally, a home and routine', () => {
  const steps = setupSteps(companion({}), null)
  assert.deepEqual(steps.map((step) => [step.id, step.done, step.optional]), [['character', true, false], ['connection', false, false], ['life', false, true]])
})

test('steps complete from the saved connection and definition', () => {
  const block = { key: 'w', label: 'Work', kind: 'work', days: [0], start: '09:00', end: '17:00', themes: [] }
  const steps = setupSteps(companion({ home_city: 'baltimore', schedule: [block] }), { model: 'qwen', base_url: 'http://localhost:1234/v1' } as Connection)
  assert.ok(steps.every((step) => step.done))
  assert.equal(steps[1].detail, 'Using qwen at http://localhost:1234/v1.')
})
