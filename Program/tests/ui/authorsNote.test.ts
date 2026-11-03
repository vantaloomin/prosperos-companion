import assert from 'node:assert/strict'
import { test } from 'node:test'
import { NOTE_SWITCH, noteKey, noteLook, noteValue } from '../../src/features/conversation/noteState.ts'
import { shortTime } from '../../src/features/conversation/clock.ts'
import { after, effect, proposals, title } from '../../src/features/sidecar/proposals.ts'

test("the author's note button is quiet when empty, lit when on, outlined when written but switched off", () => {
  assert.equal(noteLook('', true), 'off')
  assert.equal(noteLook('   ', false), 'off')
  assert.equal(noteLook('Keep it light.', true), 'on')
  assert.equal(noteLook('Keep it light.', false), 'paused')
  assert.deepEqual(noteKey('story'), ['authors-note', 'story'])
})

test("the sidecar's author's note proposal reads as the note before and after", () => {
  const [found] = proposals([{ kind: 'authors_note', chat: 'companion:c1', before: 'Old.', enabled: false, text: 'Keep it short tonight.' }], null, null, () => 'p1')
  assert.equal(found.before, 'Old.')
  assert.equal(after(found), 'Keep it short tonight.')
  assert.equal(title(found, 'Dana'), "Author's note")
  assert.match(effect(found, false), /Switches the note on/)
})

test("the note's switch is labeled by what it does, so it reads clearly on and off", () => {
  assert.equal(NOTE_SWITCH, 'Use this note')
  assert.ok(!/^(on|off)$/i.test(NOTE_SWITCH))
})

test('the + menu shows a quiet On only while a note steers replies', () => {
  assert.equal(noteValue({ text: 'Keep it cozy', enabled: true }), 'On')
  assert.equal(noteValue({ text: 'Keep it cozy', enabled: false }), undefined)
  assert.equal(noteValue({ text: '  ', enabled: true }), undefined)
})

test('the phone header time adds the weekday only when their day is not yours', () => {
  const now = new Date('2026-11-03T02:30:00Z')
  assert.doesNotMatch(shortTime('America/New_York', now, 'America/Chicago') ?? '', /Mon|Tue/)
  assert.match(shortTime('America/New_York', now, 'Europe/London') ?? '', /Mon/)
  assert.equal(shortTime('Not/AZone', now, 'UTC'), null)
})
