import assert from 'node:assert/strict'
import { test } from 'node:test'
import { bodyText, changesEmpty, eventWhen, moodText, pauseToFill, recommendationText } from '../../src/features/today/todayText.ts'
import { shortDate } from '../../src/features/today/moneyText.ts'

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
  assert.equal(storyDate('2026-10-05'), shortDate('2026-10-05'))
  assert.equal(storyDate('2026-10-05'), 'Mon, Oct 5')
  assert.deepEqual(DRAMA_LEVELS.map((level) => level.label), ['Quiet', 'Realistic', 'Dramatic', 'Soap opera'])
})

test('occasions read as a friend would say them', async () => {
  const { occasionText } = await import('../../src/features/today/storyText.ts')
  const base = { key: 'k', date: '2026-10-07', span: '', text: '', template: null }
  assert.equal(occasionText({ ...base, kind: 'user_birthday', days: 2 }, 'Mira'), 'Your birthday is in 2 days.')
  assert.equal(occasionText({ ...base, kind: 'own_birthday', days: 0 }, 'Mira'), "It is Mira's birthday today.")
  assert.equal(occasionText({ ...base, kind: 'circle_birthday', days: 1, person: 'Cathy', relation: 'mom' }, 'Mira'), "It is Mira's mom Cathy's birthday tomorrow.")
  // Milestone birthdays (Everyone gets older) say which.
  assert.equal(occasionText({ ...base, kind: 'own_birthday', days: 0, turns: 40 }, 'Mira'), "It is Mira's 40th birthday today.")
  assert.equal(occasionText({ ...base, kind: 'circle_birthday', days: 3, person: 'Cathy', relation: 'mom', turns: 60 }, 'Mira'), "It is Mira's mom Cathy's 60th birthday in 3 days.")
  assert.equal(occasionText({ ...base, kind: 'anniversary', days: 0, span: 'three months' }, 'Mira'), "It's been three months since you two started talking.")
  // A step's anniversary names the step, not the first talk (E2E v0.13).
  assert.equal(occasionText({ ...base, kind: 'step_anniversary', days: 0, span: 'a year', did: 'became exclusive' }, 'Mira'), "It's been a year since you two became exclusive.")
  assert.equal(occasionText({ ...base, kind: 'step_anniversary', days: 3, span: '2 years', did: 'swapped keys' }, 'Mira'), 'In 3 days it will be 2 years since you two swapped keys.')
})

test('the header shows one step anniversary and counts the rest (Iris, E2E v0.13)', async () => {
  const { headerOccasions } = await import('../../src/features/today/storyText.ts')
  const base = { date: '2026-10-07', span: 'a year', text: '', template: null }
  const items = [
    { ...base, key: 'b', kind: 'own_birthday' as const, days: 1 },
    { ...base, key: 's1', kind: 'step_anniversary' as const, days: 4, did: 'swapped keys' },
    { ...base, key: 's2', kind: 'step_anniversary' as const, days: 2, did: 'became exclusive' },
    { ...base, key: 's3', kind: 'step_anniversary' as const, days: 6, did: 'moved in together' },
  ]
  assert.deepEqual(headerOccasions(items, 'Mira').map((item) => item.text), [
    "It is Mira's birthday tomorrow.",
    'In 2 days it will be a year since you two became exclusive, and 2 more milestones this week.',
  ])
  assert.deepEqual(headerOccasions(items.slice(0, 2), 'Mira').map((item) => item.text)[1], 'In 4 days it will be a year since you two swapped keys.')
})

test('a home that is not on the map gets no "Show on map" (Iris, E2E v0.13)', async () => {
  const { mapPlace } = await import('../../src/features/today/todayText.ts')
  assert.equal(mapPlace({ id: '~family' }), null)
  assert.equal(mapPlace({ id: '~home' }), null)
  assert.equal(mapPlace({ id: 'p12' }), 'p12')
  assert.equal(mapPlace(null), null)
})

test('an empty "since you were last here" points at what is waiting', () => {
  assert.equal(changesEmpty('Mira', 0), "Nothing new in Mira's life yet. Quiet stretches are normal.")
  assert.equal(changesEmpty('Mira', 1), '1 thing is waiting for you above. What you keep shows up here.')
  assert.equal(changesEmpty('Mira', 3), '3 things are waiting for you above. What you keep shows up here.')
})

test('a time beside a label from their day is in their time zone', () => {
  const now = new Date('2026-11-25T12:00:00Z')
  // 6 PM in UTC is 1 PM in Baltimore: the "Afternoon" beside it reads right.
  assert.match(eventWhen('2026-11-29T18:00:00Z', now, 'America/New_York'), /1:00\sPM$/)
  assert.match(eventWhen('2026-11-25T18:00:00Z', now, 'America/New_York'), /^Today, /)
  // An outing shows its own time, not its block's start (6:00 PM · Evening).
  assert.match(eventWhen('2026-11-29T23:00:00Z', now, 'America/New_York', '18:30'), /6:30\sPM$/)
  assert.match(eventWhen('2026-11-29T23:00:00Z', now, 'America/New_York', undefined), /6:00\sPM$/)
})
