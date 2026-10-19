import assert from 'node:assert/strict'
import test from 'node:test'
import { asKindOption, foundOption, humanTermsText, kindSummary, spanChoices, yearsText } from '../../src/features/kinds/kindText.ts'
import type { KindShown } from '../../src/types.ts'

const elf: KindShown = { kind: 'elf', label: 'Elf', own: null, years: 600, kind_years: 600, life_age: 49 }

test('the kind pickers name the app pick and the kind lifespan first', () => {
  assert.equal(foundOption('Elf', 'words'), 'As their description says (Elf)')
  assert.equal(foundOption('Half-elf', 'parents'), 'From their parents (Half-elf)')
  assert.equal(foundOption('Human', 'app'), 'As the app picks (Human)')
  assert.equal(asKindOption(600), 'As their kind (about 600 years)')
  assert.equal(asKindOption(null), "As their kind (doesn't age)")
  assert.equal(yearsText(1000), '1,000 years')
})

test('the age in human terms shows only when it differs', () => {
  assert.equal(humanTermsText(elf, 312), 'About 49 in human terms.')
  assert.equal(humanTermsText({ ...elf, life_age: null }, 34), '')
  assert.equal(humanTermsText({ ...elf, life_age: 12 }, 12), '')
})

test('a picked lifespan not on the list stays offered', () => {
  assert.deepEqual(spanChoices({ kinds: [], spans: [80, 600] }, 450), [80, 450, 600])
  assert.deepEqual(spanChoices(undefined, null), [80, 150, 300, 600, 1000])
})

test('a folded kind section sums itself up', () => {
  assert.equal(kindSummary(elf), 'Kind: Elf · lives about 600 years')
  assert.equal(kindSummary({ ...elf, own: 0, years: null }), "Kind: Elf · doesn't age")
  assert.equal(kindSummary({ ...elf, kind: 'ageless', label: "Doesn't age", years: null }), "Kind: Doesn't age")
})
