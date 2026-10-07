import assert from 'node:assert/strict'
import { test } from 'node:test'
import { placeGroups } from '../../src/features/character/places.ts'
import type { CitySummary } from '../../src/types.ts'

const city = (id: string, era?: string): CitySummary => ({ id, name: id, region: 'R', country: 'C', timezone: 'UTC', summary: '', era })

test('places are grouped by era, today first, and empty eras are left out', () => {
  const groups = placeGroups([city('camelot', 'medieval'), city('baltimore', 'modern'), city('old'), city('mars', 'space opera'), city('london-1895', 'victorian')])
  assert.deepEqual(groups.map((group) => [group.label, group.cities.map((item) => item.id)]), [
    ['Today', ['baltimore', 'old']], ['Victorian', ['london-1895']], ['Medieval', ['camelot']], ['Other', ['mars']],
  ])
})
