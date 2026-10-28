import assert from 'node:assert/strict'
import { test } from 'node:test'
import { homeTitle, itemDetail, rentText, sentence, sinceText } from '../../src/features/character/homeText.ts'
import type { HomeItem } from '../../src/types.ts'

const item = (extra: Partial<HomeItem> = {}): HomeItem => ({
  id: 'i', kind: 'home', name: 'a one-bedroom in a rowhouse', variety: 'rowhouse', description: 'a one-bedroom in a rowhouse in Fells Point',
  origin: 'generated', since: '2026-10-05', until: null, edited: false, revision: 1, ...extra,
})

test('the home title is its name with the city once, and the description is a line under it', () => {
  assert.equal(homeTitle(item({ city: 'Baltimore' })), 'A one-bedroom in a rowhouse, Baltimore')
  assert.equal(homeTitle(item({ city: 'Baltimore', name: 'a flat in Baltimore' })), 'A flat in Baltimore')
  assert.equal(homeTitle(item({ city: 'Ionia', name: '', description: 'a flat above the pits.' })), 'A flat above the pits, Ionia')
  assert.equal(itemDetail(item({ description: 'a small flat above the pits, close to the crowds.' })), 'A small flat above the pits, close to the crowds.')
})

test('rent reads as an estimate and is left out without one', () => {
  assert.equal(rentText(item({ rent: 1450, rent_period: 'month', currency: { code: 'USD', symbol: '$', name: 'US dollars' } })), 'Rent about $1,450 a month (an estimate)')
  assert.equal(rentText(item({ rent: null })), null)
})

test('rent and a mortgage read in the money of their city, as the server says it', () => {
  const pennies = { code: 'penny', symbol: 'd.', name: 'silver pennies' }
  assert.equal(rentText(item({ rent: 8, rent_period: 'week', currency: pennies, rent_text: '8 d.' })), 'Rent about 8 d. a week (an estimate)')
  assert.equal(rentText(item({ rent: 12, rent_period: 'week', owned: true, currency: pennies, rent_text: '12 d.' })), 'Theirs, with a mortgage of about 12 d. a week (an estimate)')
  // No mortgage in a medieval kingdom: payments on the place.
  assert.equal(rentText(item({ rent: 12, rent_period: 'week', owned: true, medieval: true, currency: pennies, rent_text: '12 d.' })), 'Theirs, paying about 12 d. a week on it (an estimate)')
})

test('details skip a description that repeats the name and add a repair', () => {
  assert.equal(itemDetail(item({ kind: 'vehicle', name: 'the car', description: 'an old silver hatchback', out_of_action: 'in the shop until 2026-10-09' })), 'an old silver hatchback; right now in the shop until 2026-10-09')
  assert.equal(itemDetail(item({ kind: 'favorite', name: 'a record player', description: 'a record player' })), '')
})

test('since says who added a thing', () => {
  assert.equal(sinceText(item()), null)
  assert.equal(sinceText(item({ origin: 'user', since: '2026-10-06' })), 'Added by you on Oct 6, 2026')
  assert.equal(sinceText(item({ origin: 'change', since: '2026-10-20' })), 'New since Oct 20, 2026')
  assert.equal(sentence('took the car into the shop'), 'Took the car into the shop.')
})

test('housework reads in words, with the last big clean when there was one', async () => {
  const { lastClean, numbersText, upkeepSummary } = await import('../../src/features/character/upkeepText.ts')
  const areas = [
    { area: 'laundry' as const, text: 'The laundry is piling up.', value: 62 },
    { area: 'dishes' as const, text: 'The dishes are done.', value: 4 },
    { area: 'clutter' as const, text: 'The place is tidy.', value: 30 },
  ]
  assert.equal(upkeepSummary({ away: false, areas }), 'The laundry is piling up. The dishes are done. The place is tidy.')
  assert.equal(upkeepSummary({ away: true, areas }), 'They are away, so the housework waits for them.')
  assert.equal(numbersText(areas), 'Mess: Laundry 62 · Dishes 4 · Clutter 30 of 100')
  assert.equal(lastClean({ last_big_clean: null, today: '2026-10-22' }), null)
  assert.equal(lastClean({ last_big_clean: '2026-10-21', today: '2026-10-22' })?.when, 'yesterday')
  assert.match(lastClean({ last_big_clean: '2026-10-16', today: '2026-10-22' })?.when ?? '', /^\w+day$/)
  assert.match(lastClean({ last_big_clean: '2026-10-12', today: '2026-10-22' })?.when ?? '', /^last \w+day$/)
})

test('belongings use US spelling on screen', async () => {
  const { KIND_LABELS } = await import('../../src/features/character/homeText.ts')
  assert.equal(KIND_LABELS.favorite, 'Favorite thing')
  const { readFile } = await import('node:fs/promises')
  for (const file of ['features/character/homeText.ts', 'features/character/Wardrobe.tsx']) {
    assert.doesNotMatch(await readFile(new URL(`../../src/${file}`, import.meta.url), 'utf8'), /avourite/, file)
  }
})
