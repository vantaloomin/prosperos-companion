import assert from 'node:assert/strict'
import test from 'node:test'
import { actionParts, talkLine } from '../../src/features/conversation/actionText.ts'

test('actions between asterisks show without the asterisks', () => {
  assert.deepEqual(actionParts('*He grins.* Hey, Luna.'), [{ text: 'He grins.', action: true }, { text: ' Hey, Luna.', action: false }])
  assert.deepEqual(actionParts('Well. *A pause.* Mostly safe.'), [
    { text: 'Well. ', action: false }, { text: 'A pause.', action: true }, { text: ' Mostly safe.', action: false }])
})

test('bold, lone asterisks, list markers and maths stay as written', () => {
  for (const text of ['**bold** text', 'a * b * c', '* first\n* second', '5*3*2', 'no actions here']) {
    assert.deepEqual(actionParts(text), [{ text, action: false }], text)
  }
})

test('the message box says talk while together', () => {
  assert.equal(talkLine('Sett'), 'Talk to Sett')
})
