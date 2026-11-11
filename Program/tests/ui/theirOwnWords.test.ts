import assert from 'node:assert/strict'
import test from 'node:test'
import { caughtNote, caughtTitle, ruleNote, shownPhrase, type WordRule } from '../../src/features/settings/wordRulesText.ts'

test('a caught phrase says how far it has gone', () => {
  assert.equal(caughtNote({ phrase: "i'm all ears", kind: 'stock', step: 1 }), 'Stock wording')
  assert.equal(caughtNote({ phrase: 'total chaos at work', kind: 'repeat', step: 1 }), 'Repeated')
  assert.equal(caughtNote({ phrase: 'total chaos at work', kind: 'repeat', step: 2 }), 'Same question again')
  assert.equal(caughtNote({ phrase: "i'm all ears", kind: 'stock', step: 3 }), 'Now left out')
})

test('a rule on the list says what it does', () => {
  const rule = (action: WordRule['action'], replacement = ''): WordRule => ({ id: 'r', phrase: '—', action, replacement, everyone: false })
  assert.equal(ruleNote(rule('drop')), 'Dropped · this world')
  assert.equal(ruleNote({ ...rule('drop'), everyone: true }), 'Dropped · every world')
  assert.equal(ruleNote(rule('swap', ',')), 'Swapped for “,” · this world')
  assert.equal(ruleNote(rule('swap', ' ')), 'Swapped for nothing · this world')
  assert.equal(ruleNote(rule('keep')), 'Kept as theirs · this world')
})

test('caught phrases show "I" as a capital and the title names them', () => {
  assert.equal(shownPhrase("i can't help but"), "I can't help but")
  assert.equal(shownPhrase("i'm all ears"), "I'm all ears")
  assert.equal(shownPhrase('if i could'), 'if I could')
  assert.equal(shownPhrase('chuckles softly'), 'chuckles softly')
  assert.equal(caughtTitle('Dana Reyes'), 'Caught lately in Dana’s replies')
  assert.equal(caughtTitle(''), 'Caught lately')
})
