import assert from 'node:assert/strict'
import { test } from 'node:test'
import { bodyText, moodText, pauseToFill, recommendationText } from '../../src/features/today/todayText.ts'

test('the mood names its cause and the traits behind it', () => {
  const text = moodText({ id: 'm', kind: 'absence', intensity: 'moderate', away_hours: 72, traits: ['guilt over absence'], expires_at: '' }, 'Mira')
  assert.equal(text, 'Mira is in a moderate mood about the 3 days you were apart, from the traits you gave them (guilt over absence).')
})

test('only an ended pause that was not filled in is offered', () => {
  const pauses = [
    { id: 'a', started_at: '3', ended_at: null, catch_up_requested_at: null, catch_up_run_id: null },
    { id: 'b', started_at: '2', ended_at: '2.5', catch_up_requested_at: '2.6', catch_up_run_id: 'r' },
    { id: 'c', started_at: '1', ended_at: '1.5', catch_up_requested_at: null, catch_up_run_id: null },
  ]
  assert.equal(pauseToFill(pauses)?.id, 'c')
})

test('how the companion feels today reads as one line', () => {
  assert.equal(bodyText({ state: 'tired', because: 'after drinks at The Owl last night' }, 'Mira'), 'Mira is tired: after drinks at The Owl last night.')
  assert.equal(bodyText({ state: 'sick', because: 'came down with a cold' }, 'Mira'), 'Mira is under the weather: came down with a cold.')
  assert.equal(bodyText(null, 'Mira'), '')
})

test('a recommendation says where the companion is with it', () => {
  assert.equal(recommendationText({ kind: 'book', state: 'started', verdict: null }, 'Mira'), 'Mira is reading, not done yet.')
  assert.equal(recommendationText({ kind: 'show', state: 'finished', verdict: 'loved it' }, 'Mira'), 'Mira finished it and loved it.')
  assert.equal(recommendationText({ kind: 'outing', state: 'waiting', verdict: null }, 'Mira'), 'Mira means to get to it soon.')
})

test('story dates read as the local day they name', async () => {
  const { storyDate, DRAMA_LEVELS } = await import('../../src/features/today/storyText.ts')
  assert.equal(storyDate('2026-10-05'), 'Mon 5 Oct')
  assert.deepEqual(DRAMA_LEVELS.map((level) => level.label), ['Quiet', 'Realistic', 'Dramatic', 'Soap opera'])
})

test('occasions read as a friend would say them', async () => {
  const { occasionText } = await import('../../src/features/today/storyText.ts')
  const base = { key: 'k', date: '2026-10-07', span: '', text: '', template: null }
  assert.equal(occasionText({ ...base, kind: 'user_birthday', days: 2 }, 'Mira'), 'Your birthday is in 2 days.')
  assert.equal(occasionText({ ...base, kind: 'own_birthday', days: 0 }, 'Mira'), "It is Mira's birthday today.")
  assert.equal(occasionText({ ...base, kind: 'anniversary', days: 0, span: 'three months' }, 'Mira'), "It's been three months since you two started talking.")
})
