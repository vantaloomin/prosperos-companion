import assert from 'node:assert/strict'
import { test } from 'node:test'
import { petLine, petNumbers, sentenceOf } from '../../src/features/pets/petText.ts'
import { petDrafts, petsBody, petsValid } from '../../src/features/worlds/personaPetsText.ts'
import type { PetView } from '../../src/types.ts'

const pet = (change: Partial<PetView> = {}): PetView => ({
  key: 'circle:1:0', name: 'Pepper', kind: 'dog', kind_label: 'dog', looks: 'a beagle mix with floppy ears', born: '2022-01-01',
  age: '4 years old', state: 'well', status: '', died_on: null, recent: [], health: null, lifespan_years: null, ...change,
})

test('a pet line says who they are, and remembers one that died', () => {
  assert.equal(petLine(pet()), 'Pepper, a beagle mix with floppy ears, 4 years old')
  assert.equal(petLine(pet({ state: 'died' })), 'Pepper, a beagle mix with floppy ears, is remembered fondly')
  assert.equal(sentenceOf('an upset stomach'), 'An upset stomach.')
})

test('the numbers behind a pet show only when Hidden values sends them', () => {
  assert.equal(petNumbers(pet()), '')
  assert.equal(petNumbers(pet({ health: 72, lifespan_years: 13 })), 'Health 72 of 100 · usually lives about 13 years')
})

test("the user's own pets are saved as written: blank rows dropped, an age only when given", () => {
  const drafts = [...petDrafts([{ name: 'Biscuit', kind: 'cat', looks: 'one-eyed tabby', born: '2020-05-01' }]), { name: ' ', kind: 'dog', looks: '', age: '' }]
  assert.deepEqual(petsBody(drafts), [{ name: 'Biscuit', kind: 'cat', looks: 'one-eyed tabby', age: null }])
  assert.deepEqual(petsBody([{ name: 'Rex ', kind: 'dog', looks: '', age: '3' }]), [{ name: 'Rex', kind: 'dog', looks: '', age: 3 }])
  assert.equal(petsValid([{ name: 'Rex', kind: 'dog', looks: '', age: '-1' }]), false)
  assert.equal(petsValid([{ name: 'Rex', kind: 'dog', looks: '', age: '2.5' }]), false)
})
