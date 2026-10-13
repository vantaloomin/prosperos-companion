import assert from 'node:assert/strict'
import test from 'node:test'
import { HOBBY_LEVELS, gaveUpLine, hobbyNumbers, metaParts, recentLine, sourceText } from '../../src/features/character/hobbiesText.ts'
import { outingTitle, placeLine } from '../../src/features/today/outingText.ts'
import { boughtFor } from '../../src/features/today/moneyText.ts'
import type { Hobby } from '../../src/types.ts'

const hobby = (overrides: Partial<Hobby> = {}): Hobby => ({
  id: 'h1', label: 'Cello', name: 'the cello', kind: 'music', source: 'interest', status: 'active', level: 2, kept: true,
  level_text: 'Getting good at the cello', since_text: 'About two years in', status_text: 'Twice a week.', recent: [], ...overrides,
})

test('a pastime reads in words: where it came from, how far along and how often', () => {
  assert.equal(sourceText(hobby()), 'From their interests')
  assert.equal(sourceText(hobby({ source: 'app', kept: false })), 'Picked up on their own')
  assert.equal(sourceText(hobby({ source: 'app', kept: true })), 'Picked up on their own, kept')
  const names = ['just starting out', 'getting the hang of it', 'getting good', 'good at it now', 'really good']
  assert.deepEqual(metaParts(hobby(), names), { level: 'Getting good', rest: ['about two years in', 'twice a week'] })
  assert.deepEqual(metaParts(hobby({ status: 'stalled', status_text: 'Stalled lately: work got busy.' }), names), { level: 'Getting good', rest: ['about two years in'] })
  assert.deepEqual(metaParts(hobby({ status: 'dropped', status_text: 'Gave it up in March.' }), names), { level: '', rest: ['Gave it up in March'] })
  assert.equal(gaveUpLine(hobby(), 'Kim'), 'Kim gave up the cello.')
  assert.equal(recentLine('played Clair de Lune all the way through', 'Kim'), 'Kim played Clair de Lune all the way through.')
  assert.equal(hobbyNumbers(hobby()), null)
  assert.equal(hobbyNumbers(hobby({ numbers: { skill: 34, best: 36, sessions: 41, next_at: 38, talent: 1.1 } })),
    'Skill 34 of 100 (best 36), 41 sessions, next milestone at 38, talent 1.10.')
  assert.deepEqual(HOBBY_LEVELS.map((level) => level.label), ['Off', 'Light', 'True to life', 'Dramatic'])
})

test('a pastime together names itself on Today, and its fees count as pastime money', () => {
  const place = { id: '~hobby:h1', name: 'a local pond', kind: 'spot', neighborhood: '', summary: '', cost: '', cuisine: '', city: 'Baltimore',
    hobby: { id: 'h1', label: 'Fishing', session: 'went fishing', together: 'a morning of fishing', event: null, picture: '' } }
  assert.equal(outingTitle({ activity: 'hobby', place }), 'Fishing at a local pond')
  assert.equal(placeLine(place), 'Somewhere in Baltimore')
  assert.equal(boughtFor('hobby'), 'For their pastimes')
})
