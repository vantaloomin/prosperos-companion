import assert from 'node:assert/strict'
import test from 'node:test'
import { favoritesLine, mealDay, mealLine, numbersLine, parseFavorites, skillLabel } from '../../src/features/character/kitchenText.ts'
import { suggestion } from '../../src/features/map/mapText.ts'
import { placeLine } from '../../src/features/today/outingText.ts'
import { boughtFor } from '../../src/features/today/moneyText.ts'

const day = (overrides = {}) => ({ date: '2026-10-05', kind: 'cook' as const, text: 'made black bean chili', groceries: false, today: false, ...overrides })

test('the week reads as dinners, with tonight and tomorrow named', () => {
  assert.equal(mealLine(day()), 'Made black bean chili')
  assert.equal(mealLine(day({ kind: 'away', text: '' })), 'Away')
  assert.equal(mealDay(day({ today: true }), '2026-10-05'), 'Tonight')
  assert.equal(mealDay(day({ date: '2026-10-06' }), '2026-10-05'), 'Tomorrow')
  assert.match(mealDay(day({ date: '2026-10-04' }), '2026-10-05'), /4/)
})

test('favourites, skills and hidden numbers read as words', () => {
  assert.equal(favoritesLine([]), null)
  assert.equal(favoritesLine(['lasagna', 'shakshuka', 'pad see ew']), 'Dishes they make a lot: lasagna, shakshuka and pad see ew.')
  assert.deepEqual(parseFavorites(' lasagna, ,shakshuka\nramen,a,b,c'), ['lasagna', 'shakshuka', 'ramen', 'a', 'b'])
  assert.equal(skillLabel("can't really cook"), "Can't really cook")
  assert.equal(numbersLine(undefined), null)
  assert.equal(numbersLine({ rhythm: { cook: 65, takeout: 20, simple: 15 }, days_left: { coffee: 3, eggs: null } }),
    'Most nights: cooks 65%, takeout 20%, keeps it simple 15%. Days left: coffee 3.')
})

test('dinner at their place: the map drafts it, Today names it, takeout counts as dinner money', () => {
  assert.equal(suggestion({ id: '~home', name: 'Home', kind: 'home' }), 'Can I come over for dinner at your place this week?')
  assert.equal(placeLine({ id: '~home', name: "Kim's place", kind: 'home', neighborhood: 'Canton', summary: '', cost: '', cuisine: '', city: 'Baltimore' }), 'Their place in Canton')
  assert.equal(boughtFor('food'), 'For dinner')
  assert.equal(boughtFor('gift'), 'For a big day')
  assert.equal(boughtFor('funeral'), 'For a funeral')
})
