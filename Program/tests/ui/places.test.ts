import assert from 'node:assert/strict'
import { test } from 'node:test'
import { defaultCity } from '../../src/features/character/places.ts'
import type { CitySummary } from '../../src/types.ts'

const city = (id: string, era?: string): CitySummary => ({ id, name: id, region: 'R', country: 'C', timezone: 'UTC', summary: '', era })

test('a new companion gets a city of today near the user, else Baltimore', () => {
  const at = (id: string, timezone: string, era?: string): CitySummary => ({ ...city(id, era), timezone })
  const cities = [at('camelot', 'Europe/London', 'medieval'), at('baltimore', 'America/New_York'), at('los-angeles', 'America/Los_Angeles')]
  assert.equal(defaultCity(cities, 'America/Los_Angeles'), 'los-angeles')
  assert.equal(defaultCity(cities, 'America/Chicago'), 'baltimore')
  assert.equal(defaultCity(cities, 'Europe/London'), 'baltimore')
  assert.equal(defaultCity([], 'Europe/London'), '')
  // A fan pack or the user's own city of today is never picked for them.
  assert.equal(defaultCity([{ ...at('gotham', 'America/Los_Angeles'), category: 'fictional' }, ...cities], 'America/Los_Angeles'), 'los-angeles')
})
