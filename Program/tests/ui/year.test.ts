import assert from 'node:assert/strict'
import { test } from 'node:test'
import { dayText, featuredCard, firstKey, pageAt, spanText } from '../../src/features/year/yearText.ts'
import { decorationsText, nextText } from '../../src/features/character/traditionsText.ts'
import { occasionText } from '../../src/features/today/storyText.ts'

const listing = {
  periods: [{ key: 'so-far', title: 'Our year so far', start: '2026-03-10', end: '2026-10-05' },
    { key: 'year-1', title: 'Our first year', start: '2025-03-10', end: '2026-03-09' }],
  featured: null as string | null,
  featured_days: 70,
}

test('the scrapbook opens on the one Today points to, else the year so far', () => {
  assert.equal(firstKey(listing), 'so-far')
  assert.equal(firstKey({ ...listing, featured: 'year-1' }), 'year-1')
  assert.equal(firstKey({ periods: [], featured: null, featured_days: 0 }), null)
  const fresh = { ...listing, periods: [{ ...listing.periods[0], start: '2026-03-10', end: '2026-03-12' }, listing.periods[1]] }
  assert.equal(firstKey(fresh), 'year-1')
})

test('Today names the scrapbook only on the days it is featured', () => {
  assert.equal(featuredCard(listing, 'Mira'), null)
  assert.deepEqual(featuredCard({ ...listing, featured: 'year-1' }, 'Mira'), { key: 'year-1', title: 'Our first year with Mira', stat: '70 days talked' })
  assert.equal(dayText('2026-09-06'), '6 Sep')
})

test('dates and pages read plainly', () => {
  assert.equal(spanText('2025-03-10', '2026-03-09'), '10 Mar 2025 to 9 Mar 2026')
  assert.equal(pageAt(0, 600, 5), 0)
  assert.equal(pageAt(1190, 600, 5), 2)
  assert.equal(pageAt(9000, 600, 5), 4)
})

test('traditions show their next date and what is up at home', () => {
  assert.equal(nextText('2026-11-26'), 'Next: Thu 26 Nov')
  assert.equal(nextText(null), null)
  assert.equal(decorationsText(['a wreath on the front door']), 'Up at home right now: a wreath on the front door.')
  assert.equal(decorationsText(['a', 'b', 'c']), 'Up at home right now: a, b and c.')
  const item = { key: 'k', kind: 'tradition' as const, date: '2026-11-26', days: 1, span: '', text: '', template: null, holiday: 'Thanksgiving', tradition: "Always at their mom Ruth's. There's always pie.", teaser: "Thanksgiving at their mom Ruth's in Towson" }
  assert.equal(occasionText(item, 'Mira'), "Tomorrow: Thanksgiving at their mom Ruth's in Towson")
})
