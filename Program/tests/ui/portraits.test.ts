import assert from 'node:assert/strict'
import { test } from 'node:test'
import { cardNote, keepable, madeBy, redoLabel, redoable, sendsLine, setLine } from '../../src/features/appearance/portraitState.ts'
import type { GeneratedImage, Generation, PlannedShot } from '../../src/types.ts'

const codex = { id: 'b1', label: 'Codex', kind: 'codex', local: false }
const shot = (values: Partial<PlannedShot>) => ({ label: 'Profile picture', shot: '', aspect: 'portrait', prompt: '', tier: 'safe', reasons: [], route_reason: '', refusal: null, backend: codex, follows: null, ...values }) as PlannedShot
const image = (values: Partial<GeneratedImage>) => ({ id: 'i', position: 0, label: 'Profile picture', status: 'completed', decision: null, has_image: true, error: null, backend_label: 'Codex', follows: null, ...values }) as GeneratedImage
const set = (images: GeneratedImage[], status: Generation['status'] = 'completed') => ({
  id: 'g', status, images,
  counts: { completed: images.filter((item) => item.status === 'completed').length, kept: images.filter((item) => item.decision === 'kept').length },
}) as Generation

test('the plan says what leaves the computer before anything is sent', () => {
  const chain = [shot({}), shot({ follows: 0 }), shot({ follows: 0 })]
  assert.match(sendsLine(chain, false), /All three go to Codex\. Pictures 2 and 3 each send picture 1 along/)
  assert.match(sendsLine(chain.map((item) => ({ ...item, follows: null })), true), /descriptions only, so they may not look like the same person/)
  assert.equal(sendsLine([shot({ backend: null, refusal: 'No backend.' })], false), 'No backend.')
})

test('a set reads as what happened, and only finished pictures can be kept', () => {
  const running = set([image({}), image({ id: 'j', position: 1, status: 'running', label: 'Three-quarter view' }), image({ id: 'k', position: 2, status: 'queued' })], 'running')
  assert.equal(setLine(running), 'Making picture 2 of 3: three-quarter view.')
  const partial = set([image({}), image({ id: 'j', position: 1, status: 'failed', error: 'Quota' }), image({ id: 'k', position: 2, status: 'failed' })])
  assert.equal(setLine(partial), '1 made, 2 not made. Make the missing ones again, or keep what you have.')
  assert.deepEqual(keepable(partial).map((item) => item.id), ['i'])
  const kept = set([image({ decision: 'kept' }), image({ id: 'j', position: 1, decision: 'kept' }), image({ id: 'k', position: 2, decision: 'kept' })])
  assert.equal(setLine(kept), 'Kept 3 pictures.')
  assert.deepEqual(keepable(kept), [])
})

test('cards explain waiting pictures and what each followed', () => {
  assert.equal(cardNote(image({ status: 'queued', position: 2, follows: 0, has_image: false })), 'Waiting for picture 1.')
  assert.equal(cardNote(image({ status: 'failed', error: 'Picture 2 did not finish' })), 'Picture 2 did not finish')
  assert.equal(madeBy(image({ follows: 0 })), 'Codex, from picture 1')
  assert.equal(madeBy(image({})), 'Codex')
  const images = [image({}), image({ id: 'j', position: 1, follows: 0 }), image({ id: 'k', position: 2, follows: 0, decision: 'kept' })]
  assert.equal(redoLabel(images[1], images), 'Make this one again')
  assert.equal(redoLabel(images[0], images), 'Make this and the pictures made from it again')
  assert.equal(redoable(images[1], images), true)
  assert.equal(redoable(images[0], images), false)
})
