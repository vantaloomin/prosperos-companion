import assert from 'node:assert/strict'
import { test } from 'node:test'
import { fieldLine, splitFields, studyVersionLabel, type StudyField } from '../../src/features/character/studyReview.ts'

const copied: StudyField = { source: 'text', label: 'Character & background', target: 'background', target_label: 'Background', status: 'copied', characters: 1200, note: '' }
const name: StudyField = { source: 'name', label: 'Name', target: 'name', target_label: 'Name', status: 'copied', characters: 4, note: '' }
const left: StudyField = { source: 'scenario', label: 'Scenario', target: null, target_label: null, status: 'not_imported', characters: null, note: 'Stays in the Study.' }

test('copied fields are separated from fields that stay in the Study', () => {
  const { included, left: kept } = splitFields([name, copied, left])
  assert.deepEqual(included.map((field) => field.source), ['name', 'text'])
  assert.deepEqual(kept.map((field) => field.source), ['scenario'])
})

test('a field line names where the text goes and how long it is', () => {
  assert.equal(fieldLine(copied), 'Character & background → Background (1,200 characters)')
  assert.equal(fieldLine(name), 'Name (4 characters)')
  assert.equal(fieldLine(left), 'Scenario: Stays in the Study.')
  assert.match(fieldLine({ ...copied, status: 'shortened', note: 'Kept the first 12,000.' }), /Kept the first 12,000\.$/)
})

test('a workspace without a recorded version says so', () => {
  assert.equal(studyVersionLabel({ path: '/s', database: '/s/db', study_version: '', schema_fingerprint: 'abc' }), 'Study version not recorded')
  assert.equal(studyVersionLabel({ path: '/s', database: '/s/db', study_version: '0.9.0', schema_fingerprint: 'abc' }), 'Study 0.9.0')
})
