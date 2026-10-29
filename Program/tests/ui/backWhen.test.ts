import { test } from 'node:test'
import assert from 'node:assert/strict'
import { backWhenNote, backWhenYears, firstPick, firstYear, momentLine, pickedYear } from '../../src/features/character/backWhenText.ts'
import { defaultPastYear, pastYears, whereLine, worldLabel, yearBadge } from '../../src/features/worlds/worldsText.ts'

const met = { key: 'met', label: 'When you first met', year: 2019, name: 'Back when · 2019', age: 31 }
const round = { key: 'age:25', label: 'When Dana was 25', year: 2013, name: 'Back when · 2013', age: 25 }

test('the sheet opens on the app\'s first moment, or a year when it found none', () => {
  assert.deepEqual(firstPick({ moments: [met, round] }), { kind: 'moment', key: 'met' })
  assert.deepEqual(firstPick({ moments: [] }), { kind: 'year' })
  assert.equal(pickedYear({ moments: [met, round] }, { kind: 'moment', key: 'age:25' }, 2001), 2013)
  assert.equal(pickedYear({ moments: [met] }, { kind: 'year' }, 2001), 2001)
})

test('the year picker lists every allowed year, latest first, and starts in the middle', () => {
  assert.deepEqual(backWhenYears({ earliest: 2020, latest: 2023 }), [2023, 2022, 2021, 2020])
  assert.deepEqual(backWhenYears({ earliest: 2026, latest: 2025 }), [])
  assert.equal(firstYear({ earliest: 1990, latest: 2025 }), 2008)
})

test('a moment says the year and their age then, once', () => {
  assert.equal(momentLine(met, 'Dana Reyes'), '2019 · Dana was 31')
  assert.equal(momentLine(round, 'Dana Reyes'), '2013')
  assert.equal(momentLine({ ...met, age: null }, 'Dana'), '2019')
  assert.match(backWhenNote('Dana'), /with Dana/)
})

test('a world in a past year shows the year it is there', () => {
  assert.equal(worldLabel({ name: 'Grandport', year: 2009 }), 'Grandport · 2009')
  assert.equal(worldLabel({ name: 'Back when · 2009', year: 2009 }), 'Back when · 2009')
  assert.equal(worldLabel({ name: 'Grandport', year: null }), 'Grandport')
  assert.equal(whereLine({ name: 'Sam' }, { name: 'Grandport', year: 1997 }), 'Sam · Grandport · 1997')
  assert.deepEqual(yearBadge({ year: 2010 }), { text: '2010', label: "It's 2010 there" })
  assert.equal(yearBadge({ year: null }), null)
})

test('a new world can start any year from last year back to 1990, ten years back first', () => {
  const years = pastYears(2026)
  assert.equal(years[0], 2025)
  assert.equal(years[years.length - 1], 1990)
  assert.equal(years.length, 36)
  assert.equal(defaultPastYear(2026), 2016)
  assert.equal(defaultPastYear(1995), 1990)
})
