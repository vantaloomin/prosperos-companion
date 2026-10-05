import assert from 'node:assert/strict'
import { test } from 'node:test'
import { checkpointLine, cropPixels, dhash, evaluationRows, formatBytes, grayscale, progressLine, reviewLine } from '../../src/features/appearance/loraState.ts'
import type { EvalImage, TrainingRun } from '../../src/types.ts'

test('the difference hash compares neighbours left to right', () => {
  const rising = Array.from({ length: 72 }, (_value, index) => index % 9)
  assert.equal(dhash(rising), 'ffffffffffffffff')
  assert.equal(dhash(rising.map((value) => -value)), '0000000000000000')
  assert.throws(() => dhash([1, 2, 3]))
  assert.deepEqual(grayscale([255, 255, 255, 255, 0, 0, 0, 255]).map(Math.round), [255, 0])
})

test('crops stay inside the picture', () => {
  assert.deepEqual(cropPixels({ x: 0.5, y: 0.5, width: 0.8, height: 0.2 }, 1000, 500), { x: 500, y: 250, width: 500, height: 100 })
})

const run = (values: Partial<TrainingRun>) => ({ status: 'running', progress_step: null, progress_total: null, checkpoints: [], error: null, resumable: false, restartable: false, ...values }) as TrainingRun

test('progress is only what the trainer reported', () => {
  assert.equal(progressLine(run({})), 'Starting. Progress appears when the trainer reports it.')
  assert.equal(progressLine(run({ progress_step: 120, progress_total: 1500 })), 'Step 120 of 1500, as the trainer reported.')
  const checkpoint = { step: 250, final: false, file: 'a', bytes: 2048, verified: true, format: 'lokr', sha256: 'x', problem: null }
  assert.equal(progressLine(run({ status: 'failed', error: 'Out of memory.', resumable: true, restartable: true, checkpoints: [checkpoint] })), 'Out of memory. 1 verified checkpoint can be resumed.')
  assert.equal(progressLine(run({ status: 'interrupted', restartable: true })), 'Interrupted. No verified checkpoint, so it can only restart.')
  assert.equal(checkpointLine(checkpoint), 'Step 250 · 2 KB · checked')
  assert.equal(checkpointLine({ ...checkpoint, verified: false, problem: 'incomplete' }), 'Step 250 · failed the check: incomplete')
})

test('sizes and review lines read plainly', () => {
  assert.equal(formatBytes(3 * 1024 ** 3), '3.0 GB')
  assert.equal(formatBytes(150 * 1024 ** 2), '150.0 MB')
  assert.equal(reviewLine({ training: 20, evaluation: 2, excluded: 1, blocking: [], advice: [], ready: true }), 'Ready to train: 20 training, 2 held out for evaluation, 1 excluded.')
})

test('evaluation images pair up by prompt', () => {
  const image = (key: string, variant: 'lora' | 'text', position: number) => ({ id: `${key}-${variant}`, prompt_key: key, label: key, variant, position }) as EvalImage
  const rows = evaluationRows([image('b', 'text', 3), image('a', 'lora', 0), image('b', 'lora', 1), image('a', 'text', 2)])
  assert.deepEqual(rows.map((row) => [row.key, row.lora?.id, row.text?.id]), [['a', 'a-lora', 'a-text'], ['b', 'b-lora', 'b-text']])
})
