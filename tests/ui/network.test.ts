import assert from 'node:assert/strict'
import { test } from 'node:test'
import { metLine, networkLine } from '../../src/features/today/networkText.ts'

test('a friend of a friend reads as how they are connected', () => {
  assert.equal(networkLine({ how: "Becca's coworker", age: 41, occupation: 'nurse' }), "Becca's coworker, 41, nurse")
  assert.equal(networkLine({ how: "Becca's roommate", age: 29, occupation: '' }), "Becca's roommate, 29")
})

test('a meeting names the occasion and day', () => {
  assert.match(metLine({ occasion: "Becca's Friendsgiving", met_on: '2026-11-21' }), /^Met at Becca's Friendsgiving on (21 November|November 21)\.$/)
})
