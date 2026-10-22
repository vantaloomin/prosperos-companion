import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import { MODERN_WORDS, capital, say, type EraWords } from '../../src/features/world/eraWords.ts'
import { callActions, callLine, type WhereCall } from '../../src/features/conversation/whereText.ts'
import { photoAlt, photoLine } from '../../src/features/conversation/photoState.ts'
import { profileTabs } from '../../src/features/profile/profileText.ts'
import type { ChatPhoto } from '../../src/types'

const table = JSON.parse(readFileSync(new URL('../../companion/world/data/era_words.json', import.meta.url), 'utf8'))
const words = (group: string): EraWords => ({ ...table.words.modern, ...table.words[group] })

test("today's words on screen are the word table's modern ones, and every era group has every word", () => {
  assert.deepEqual(MODERN_WORDS, table.words.modern)
  for (const group of ['historical', 'fantasy', 'future']) assert.deepEqual(Object.keys(table.words[group]).sort(), Object.keys(MODERN_WORDS).sort(), group)
})

test('a word fills in the name, and an unknown word falls back to today\'s', () => {
  assert.equal(say(words('fantasy'), 'message_to', 'Gwen'), 'Write a letter to Gwen')
  assert.equal(say(words('historical'), 'call_on', 'Alfie'), 'On the telephone with Alfie')
  assert.equal(say({} as EraWords, 'message_to', 'Sam'), 'Message Sam')
  assert.equal(capital('photograph'), 'Photograph')
})

test('a call reads in the era: the telephone in 1925, the speaking stone in a fantasy town', () => {
  const call = { id: 'c', status: 'on', direction: 'you' } as WhereCall
  assert.equal(callLine(call, 'Alfie', words('historical')).lead, 'On the telephone with Alfie')
  assert.deepEqual(callActions(call, words('historical')).map((item) => item.label), ['Hang up'])
  assert.equal(callLine({ ...call, status: 'missed', direction: 'them' }, 'Gwen', words('fantasy')).lead, 'Gwen reached for you by stone, and you missed it.')
  assert.equal(callLine(call, 'Sam').lead, 'On a call with Sam')
  assert.deepEqual(callActions({ ...call, status: 'missed', direction: 'them' }).map((item) => item.label), ['Call back'])
})

test('pictures and the profile tabs take the era words', () => {
  const photo = { kind: 'view', status: 'queued', summary: 'the harbour' } as ChatPhoto
  assert.equal(photoAlt('Alfie', photo, words('historical')), 'Photograph of the view from Alfie: the harbour')
  assert.equal(photoLine({ ...photo, kind: 'selfie' }, words('fantasy')), 'The likeness is on its way.')
  assert.equal(photoLine(photo), 'The photo is on its way.')
  assert.deepEqual(profileTabs(words('fantasy')).map((tab) => tab.label), ['Letters', 'Chronicle', 'Memories', 'Character'])
  assert.deepEqual(profileTabs(words('future')).map((tab) => tab.label), ['Comms', 'Posts', 'Memories', 'Character'])
})
