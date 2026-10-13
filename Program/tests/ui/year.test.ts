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
  assert.equal(dayText('2026-09-06'), 'Sep 6')
})

test('dates and pages read plainly', () => {
  assert.equal(spanText('2025-03-10', '2026-03-09'), 'Mar 10, 2025 to Mar 9, 2026')
  assert.equal(spanText('2026-03-10', '2026-09-06'), 'Mar 10 to Sep 6, 2026')
  assert.equal(spanText('2026-10-12', '2026-10-12'), 'Oct 12, 2026')
  assert.equal(pageAt(0, 600, 5), 0)
  assert.equal(pageAt(1190, 600, 5), 2)
  assert.equal(pageAt(9000, 600, 5), 4)
})

test('traditions show their next date and what is up at home', () => {
  assert.equal(nextText('2026-11-26'), 'Next: Thu, Nov 26')
  assert.equal(nextText(null), null)
  assert.equal(decorationsText(['a wreath on the front door']), 'Up at home right now: a wreath on the front door.')
  assert.equal(decorationsText(['a', 'b', 'c']), 'Up at home right now: a, b and c.')
  const item = { key: 'k', kind: 'tradition' as const, date: '2026-11-26', days: 1, span: '', text: '', template: null, holiday: 'Thanksgiving', tradition: "Always at their mom Ruth's. There's always pie.", teaser: "Thanksgiving at their mom Ruth's in Towson" }
  assert.equal(occasionText(item, 'Mira'), "Tomorrow: Thanksgiving at their mom Ruth's in Towson.")
})

test('history lines name their stretch and come newest first by year', async () => {
  const { byYear, stretchText } = await import('../../src/features/year/yearText.ts')
  assert.equal(stretchText({ key: 'w2026-10-05', kind: 'week', start: '2026-10-05', end: '2026-10-11' }), `Week of ${dayText('2026-10-05')}`)
  assert.equal(stretchText({ key: 'w2026-10-05', kind: 'week', start: '2026-10-07', end: '2026-10-11' }), `Week of ${dayText('2026-10-05')}`)
  assert.equal(stretchText({ key: 'w2026-10-12', kind: 'week', start: '2026-10-12', end: '2026-10-25' }), spanText('2026-10-12', '2026-10-25'))
  assert.equal(stretchText({ key: 'y2025', kind: 'year', start: '2025-03-02', end: '2025-12-31' }), '2025')
  assert.equal(stretchText({ key: 'y2023', kind: 'year', start: '2023-01-01', end: '2024-12-31' }), '2023 to 2024')
  assert.match(stretchText({ key: 'm2026-06', kind: 'month', start: '2026-06-01', end: '2026-07-31' }), / to /)
  const groups = byYear([{ start: '2025-12-01' }, { start: '2026-01-01' }, { start: '2026-02-01' }])
  assert.deepEqual(groups.map((group) => [group.year, group.lines.map((line) => line.start)]), [['2026', ['2026-02-01', '2026-01-01']], ['2025', ['2025-12-01']]])
})
