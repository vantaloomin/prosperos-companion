import assert from 'node:assert/strict'
import { test } from 'node:test'
import { homeTitle, itemDetail, rentText, sentence, sinceText } from '../../src/features/character/homeText.ts'
import type { HomeItem } from '../../src/types.ts'

const item = (extra: Partial<HomeItem> = {}): HomeItem => ({
  id: 'i', kind: 'home', name: 'a one-bedroom in a rowhouse', variety: 'rowhouse', description: 'a one-bedroom in a rowhouse in Fells Point',
  origin: 'generated', since: '2026-10-05', until: null, edited: false, revision: 1, ...extra,
})

test('the home title adds the city once and starts with a capital', () => {
  assert.equal(homeTitle(item({ city: 'Baltimore' })), 'A one-bedroom in a rowhouse in Fells Point, Baltimore')
  assert.equal(homeTitle(item({ city: 'Baltimore', description: 'a flat in Baltimore' })), 'A flat in Baltimore')
})

test('rent reads as an estimate and is left out without one', () => {
  assert.equal(rentText(item({ rent: 1450, rent_period: 'month', currency: { code: 'USD', symbol: '$', name: 'US dollars' } })), 'Rent about $1,450 a month (an estimate)')
  assert.equal(rentText(item({ rent: null })), null)
})

test('details skip a description that repeats the name and add a repair', () => {
  assert.equal(itemDetail(item({ kind: 'vehicle', name: 'the car', description: 'an old silver hatchback', out_of_action: 'in the shop until 2026-10-09' })), 'an old silver hatchback; right now in the shop until 2026-10-09')
  assert.equal(itemDetail(item({ kind: 'favorite', name: 'a record player', description: 'a record player' })), '')
})

test('since says who added a thing', () => {
  assert.equal(sinceText(item()), null)
  assert.equal(sinceText(item({ origin: 'user', since: '2026-10-06' })), 'Added by you on 2026-10-06')
  assert.equal(sinceText(item({ origin: 'change', since: '2026-10-20' })), 'New since 2026-10-20')
  assert.equal(sentence('took the car into the shop'), 'Took the car into the shop.')
})
