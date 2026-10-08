import assert from 'node:assert/strict'
import { test } from 'node:test'
import { failureText } from '../../src/features/groups/groupText.ts'
import { canForget, formBody, formFrom, guardNote, howText, keptLine, knowsLine, wordsFrom } from '../../src/features/groups/secretText.ts'
import type { Secret, SecretHolder } from '../../src/types.ts'

const holder = (name: string, via: SecretHolder['via'], extra: Partial<SecretHolder> = {}): SecretHolder =>
  ({ key: `companion:${name}`, companion_id: name, name: `${name} Hart`, via, how: via === 'origin' ? 'from the start' : 'heard it in a group', learned_at: '', group: null, ...extra })
const secret: Secret = {
  id: 's', kind: 'declared', statement: 'Billy and Katie have been secretly seeing each other', source: 'You added this', about: ['Billy Hart', 'Katie'],
  key_words: ['seeing'], own_key_words: [], keep_from_everyone: false, knows: [holder('Billy', 'origin')],
  kept_from: [{ key: 'companion:Sally', companion_id: 'Sally', name: 'Sally Moss' }], created_at: '',
}

test('the panel says who knows a secret and who it is kept from', () => {
  assert.equal(knowsLine(secret), 'Known to you and Billy (from the start)')
  assert.equal(knowsLine({ knows: [] }), 'Known to you')
  assert.equal(keptLine(secret), 'Kept from Sally')
  assert.equal(keptLine({ ...secret, keep_from_everyone: true }), 'Kept from everyone else')
  assert.equal(keptLine({ ...secret, kept_from: [] }), 'Not kept from anyone in particular')
  assert.equal(keptLine({ ...secret, kept_from: [], knows: [...secret.knows, holder('Sally', 'slip')] }), 'Everyone it was kept from knows now')
  assert.equal(howText(holder('Sally', 'witness', { group: { id: 'g', name: 'Friday crew' } })), 'heard it in Friday crew')
  assert.equal(howText(holder('Sally', 'slip', { group: { id: 'g', name: '' }, how: 'it slipped out in a group' })), 'it slipped out in a group')
})

test('only what someone learned can be forgotten, not what happened in their own life', () => {
  assert.equal(canForget(secret, holder('Billy', 'origin')), true)
  assert.equal(canForget({ kind: 'storyline' }, holder('Billy', 'origin')), false)
  assert.equal(canForget({ kind: 'storyline' }, holder('Sally', 'slip')), true)
  assert.equal(canForget(secret, { via: 'witness', companion_id: null }), false)
})

test('the form round-trips a secret and never keeps someone from what they know', () => {
  const form = formFrom(secret)
  assert.deepEqual(form, { statement: secret.statement, about: 'Billy Hart, Katie', knows: ['Billy'], kept: ['Sally'], everyone: false, words: '' })
  assert.deepEqual(formBody({ ...form, kept: ['Sally', 'Billy'], words: 'Dating, kissed, dating' }, true), {
    statement: secret.statement, about: ['Billy Hart', 'Katie'], knows: ['Billy'], kept_from: ['Sally'], keep_from_everyone: false, key_words: ['dating', 'kissed'],
  })
  assert.deepEqual(formBody({ ...form, everyone: true }, false), { kept_from: [], keep_from_everyone: true, key_words: [] })
  assert.deepEqual(wordsFrom(' a , ,B'), ['a', 'b'])
})

test('a reply the check touched says what happened', () => {
  const reply = { id: 'm', seq: 2, kind: 'companion' as const, companion_id: 'Billy', name: 'Billy', text: '', reply_to: 'u', created_at: '' }
  assert.equal(failureText({ ...reply, status: 'cancelled', error: null, guard: 'held' }), "Billy nearly let a secret slip, so this reply wasn't sent.")
  assert.equal(guardNote({ name: 'Billy', status: 'complete', guard: 'revealed' }), 'Billy let a secret slip. Everyone here knows it now.')
  assert.equal(guardNote({ name: 'Billy', status: 'complete', guard: 'redrafted' }), null)
})
