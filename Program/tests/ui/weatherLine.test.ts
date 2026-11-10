import assert from 'node:assert/strict'
import { test } from 'node:test'
import { dayWeatherText, weatherLine } from '../../src/features/today/todayText.ts'

test("the Now card names today's sky, how long a spell has held, and tomorrow", () => {
  const day = { date: '2026-01-14', body: null,
    weather: { sky: 'rain' as const, days: 3, high_f: 48, low_f: 37, rain: true },
    tomorrow: { sky: 'storm' as const, days: 1, high_f: 52, low_f: 40, rain: true } }
  assert.deepEqual(weatherLine(day), { full: 'Rain for 3 days, high 48° · Tomorrow: storms, high 52°', short: 'Rain for 3 days, high 48°F' })
  assert.deepEqual(weatherLine({ ...day, tomorrow: null }), { full: 'Rain for 3 days, high 48°F', short: 'Rain for 3 days, high 48°F' })
})

test('sunny spells are not counted, a day planned before skies were named says wet or dry, a lookup says so', () => {
  assert.equal(dayWeatherText({ sky: 'clear', days: 4, high_f: 70, low_f: 55, rain: false }), 'Clear, high 70°F')
  assert.equal(dayWeatherText({ high_f: 70, low_f: 55, rain: false }), 'Dry, high 70°F')
  assert.equal(dayWeatherText({ sky: 'fog', high_f: 50, low_f: 44, rain: false, observed: { source: 'Open-Meteo' } }), 'Fog, high 50°F (looked up)')
  assert.equal(dayWeatherText({ sky: 'snow', high_f: 30, low_f: 22, rain: true, observed: { source: 'Open-Meteo', forecast: true } }), 'Snow, high 30°F (forecast)')
})

test('no weather (aboard a ship) is no line', () => {
  assert.deepEqual(weatherLine({ date: '2026-01-14', body: null, weather: null, tomorrow: null }), { full: '', short: '' })
})
