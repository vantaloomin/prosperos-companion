import assert from 'node:assert/strict'
import { test } from 'node:test'
import { SETTINGS_TABS, availableTabs, pickTab, searchSettings } from '../../src/features/settings/sections.ts'
import { setupSteps } from '../../src/features/conversation/setup.ts'
import type { Companion } from '../../src/types.ts'

test('a deep link opens its tab, and an unknown or unavailable one opens the first', () => {
  assert.equal(pickTab('images', true), 'images')
  assert.equal(pickTab(undefined, true), 'general')
  assert.equal(pickTab('nonsense', true), 'general')
  // Before a companion exists only the model settings can be changed.
  assert.equal(pickTab('images', false), 'models')
  assert.deepEqual(availableTabs(false).map((tab) => tab.id), ['models'])
})

test('search finds sections by title, tab name or keyword, needing every word', () => {
  const found = (query: string, hasCompanion = true) => searchSettings(query, hasCompanion).map((match) => match.section.heading)
  assert.deepEqual(found('timezone'), ['time-heading'])
  assert.deepEqual(found('WEATHER'), ['context-heading'])
  assert.deepEqual(found('restore'), ['backup-heading'])
  assert.ok(found('quiet hours').includes('notifications-heading'))
  assert.deepEqual(found('anthropic key'), ['models-heading'])
  assert.deepEqual(found('weather', false), [])
  assert.deepEqual(found('   '), [])
})

test('every section heading is listed once', () => {
  const headings = SETTINGS_TABS.flatMap((tab) => tab.sections.map((section) => section.heading))
  assert.equal(new Set(headings).size, headings.length)
})

test('the setup checklist sends you straight to the Models tab', () => {
  const companion = { version: { name: 'Mira', definition: { home_city: '', schedule: [] } } } as unknown as Companion
  assert.equal(setupSteps(companion, null).find((step) => step.id === 'connection')?.view, 'settings/models')
})
