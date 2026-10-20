import { test } from 'node:test'
import assert from 'node:assert/strict'
import type { WatchFocus, WatchLine } from '../../src/types.ts'
import { firstName, focusGroups, INNER_VOICE_LEVELS, lineTime, stepInLabel } from '../../src/features/watch/watchText.ts'

const person = (key: string, name: string, kind: WatchFocus['kind']) => ({ key, name, kind, line: '' }) as unknown as WatchFocus

test('the Focus picker lists companions first, then townsfolk, and skips an empty group', () => {
  const groups = focusGroups([person('town:a', 'Ada Moss', 'townsperson'), person('companion:1', 'Rin Hale', 'companion')])
  assert.deepEqual(groups.map((group) => [group.label, group.people.map((item) => item.key)]), [['Companions', ['companion:1']], ['Around town', ['town:a']]])
  assert.deepEqual(focusGroups([person('town:a', 'Ada', 'townsperson')]).map((group) => group.label), ['Around town'])
})

test('stepping in talks to a companion and becomes a townsperson, by first name', () => {
  assert.equal(stepInLabel(person('companion:1', 'Rin Hale', 'companion')), 'Talk to Rin')
  assert.equal(stepInLabel(person('town:a', 'Ada Moss', 'townsperson')), 'Become Ada')
  assert.equal(firstName('  Ada   Moss '), 'Ada')
})

test('line times read in the town clock, how they feel reads Now, and a bad zone still shows a time', () => {
  const line = { id: '1', kind: 'event', at: '2026-10-20T13:30:00Z', text: '', inner: '', numbers: [] } as unknown as WatchLine
  assert.match(lineTime(line, 'UTC'), /1:30/)
  assert.equal(lineTime({ ...line, kind: 'mood' }, 'UTC'), 'Now')
  assert.ok(lineTime(line, 'Not/AZone').length > 0)
})

test('the Inner voice slider has four steps, from just what happened to everything on their mind', () => {
  assert.deepEqual(INNER_VOICE_LEVELS.map((level) => level.label), ['Just what happened', 'A few thoughts', 'True to life', 'Everything on their mind'])
})
