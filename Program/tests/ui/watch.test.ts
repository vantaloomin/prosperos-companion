import { test } from 'node:test'
import assert from 'node:assert/strict'
import type { WatchFocus, WatchLine } from '../../src/types.ts'
import { becomeLabel, firstName, focusGroups, inChat, INNER_VOICE_LEVELS, lineTime, stepInLabel } from '../../src/features/watch/watchText.ts'

const person = (key: string, name: string, kind: WatchFocus['kind'], extra: Partial<WatchFocus> = {}) => ({ key, name, kind, line: '', ...extra }) as unknown as WatchFocus

test('the Focus picker lists companions first, then townsfolk, and skips an empty group', () => {
  const groups = focusGroups([person('town:a', 'Ada Moss', 'townsperson'), person('companion:1', 'Rin Hale', 'companion')])
  assert.deepEqual(groups.map((group) => [group.label, group.people.map((item) => item.key)]), [['Companions', ['companion:1']], ['Around town', ['town:a']]])
  assert.deepEqual(focusGroups([person('town:a', 'Ada', 'townsperson')]).map((group) => group.label), ['Around town'])
})

test('the groups say where each person comes from: a circle, met by the companion, or a busy week', () => {
  const groups = focusGroups([
    person('town:b', 'Bo Lin', 'townsperson', { source: 'busy' }),
    person('town:m', 'Mae Ro', 'townsperson', { source: 'met', owner: 'Sett' }),
    person('circle:1', 'Ana Kay', 'circle', { owner: 'Sett' }),
    person('circle:2', 'Cy Doe', 'circle', { owner: 'Rin' }),
    person('companion:1', 'Sett', 'companion'),
  ])
  assert.deepEqual(groups.map((group) => [group.label, group.people.map((item) => item.key)]), [
    ['Companions', ['companion:1']], ["Sett's people", ['circle:1']], ["Rin's people", ['circle:2']],
    ['Sett has met', ['town:m']], ['Busy around town this week', ['town:b']],
  ])
})

test('stepping in talks to a companion, and a townsperson is offered as something to try, by first name', () => {
  assert.equal(stepInLabel(person('companion:1', 'Rin Hale', 'companion')), 'Talk to Rin')
  assert.equal(becomeLabel('Ada Moss'), 'Try life as Ada')
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

test('the Just watching banner shows only in chats, where writing would step you back in', () => {
  assert.ok(inChat('conversation') && inChat('group/abc'))
  assert.ok(!inChat('worlds') && !inChat('dating') && !inChat('settings/realism') && !inChat('watch'))
})
