import assert from 'node:assert/strict'
import { test } from 'node:test'
import { calendarDay, clockTime, dayAndClock, exactTime, relativeTime } from '../../src/when.ts'

const at = (day: number, hour: number, minute = 0, second = 0) => new Date(2026, 9, day, hour, minute, second).getTime()
const iso = (ms: number) => new Date(ms).toISOString()
const now = at(8, 21, 30)

test('recent messages read as minutes or hours ago', () => {
  assert.equal(relativeTime(iso(now - 20_000), now), 'just now')
  assert.equal(relativeTime(iso(now + 20_000), now), 'just now')
  assert.equal(relativeTime(iso(now - 60_000), now), '1 minute ago')
  assert.equal(relativeTime(iso(now - 5 * 60_000), now), '5 minutes ago')
  assert.equal(relativeTime(iso(at(8, 19, 0)), now), '2 hours ago')
})

test('older ones show the clock, yesterday, the weekday, then the date', () => {
  const clock = (ms: number) => clockTime(iso(ms), ms)
  assert.equal(relativeTime(iso(at(8, 9, 14)), now), clock(at(8, 9, 14)))
  assert.equal(relativeTime(iso(at(7, 23, 50)), now), `Yesterday ${clock(at(7, 23, 50))}`)
  assert.match(relativeTime(iso(at(5, 9, 14)), now), /^\S+ /)
  assert.ok(relativeTime(iso(at(5, 9, 14)), now).endsWith(clock(at(5, 9, 14))))
  assert.ok(relativeTime(iso(new Date(2025, 2, 3, 9).getTime()), now).includes('2025'))
  assert.ok(!relativeTime(iso(at(1, 9)), now).includes('2026'))
})

test('a time ahead of the app clock shows when it is, and bad input shows nothing', () => {
  assert.equal(relativeTime(iso(at(8, 23)), now), clockTime(iso(at(8, 23)), now))
  assert.equal(relativeTime('nonsense', now), '')
  assert.ok(exactTime(iso(now)).includes('2026'))
})

test('Retro IM shows the clock today and the date before it on older messages', () => {
  assert.ok(!clockTime(iso(at(8, 9, 14)), now).includes(','))
  assert.ok(clockTime(iso(at(5, 9, 14)), now).startsWith(clockTime(iso(at(5, 9, 14)), now).split(',')[0]))
  assert.ok(clockTime(iso(at(5, 9, 14)), now).includes(', '))
  assert.ok(clockTime(iso(new Date(2025, 2, 3, 9).getTime()), now).includes('2025'))
})

test('a lookup time always shows its day and clock, the year only when it differs', () => {
  assert.ok(dayAndClock(iso(at(8, 9, 14)), now).includes(', '))
  assert.ok(!dayAndClock(iso(at(8, 9, 14)), now).includes('2026'))
  assert.ok(!dayAndClock(iso(at(8, 9, 14, 30)), now).includes(':30'))
  assert.ok(dayAndClock(iso(new Date(2025, 2, 3, 9).getTime()), now).includes('2025'))
  assert.equal(dayAndClock('nonsense', now), '')
})

test('calendar days read month first in en-US, without shifting through a timezone', () => {
  assert.equal(calendarDay('2026-11-26'), 'Nov 26')
  assert.equal(calendarDay('2026-11-26', { weekday: true }), 'Thu, Nov 26')
  assert.equal(calendarDay('2025-03-10', { year: true }), 'Mar 10, 2025')
  assert.equal(calendarDay('2026-01-01', { month: 'long', year: true }), 'January 1, 2026')
  assert.equal(calendarDay('2026-09-06T23:30:00'), 'Sep 6')
})

test('dates follow the user\'s locale: no screen hard-codes a day-month (en-GB) format', async () => {
  const { readdir, readFile } = await import('node:fs/promises')
  const files = (await readdir(new URL('../../src', import.meta.url), { recursive: true })).filter((file) => /\.tsx?$/.test(file))
  for (const file of files) {
    const text = await readFile(new URL(`../../src/${file}`, import.meta.url), 'utf8')
    assert.doesNotMatch(text, /['"]en-GB['"]/, file)
    assert.doesNotMatch(text, /\[\s*'Jan',\s*'Feb'/, `${file} spells months itself; use calendarDay`)
  }
})
