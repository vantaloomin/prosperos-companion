import assert from 'node:assert/strict'
import { test } from 'node:test'
import { SETTINGS_TABS, availableTabs, pickTab, searchSettings } from '../../src/features/settings/sections.ts'
import { readAdvanced, writeAdvanced } from '../../src/features/settings/advanced.ts'
import { groupPrompts, placeholderHint } from '../../src/features/settings/prompts.ts'
import { setupSteps } from '../../src/features/conversation/setup.ts'
import type { Companion, LifeSettings, WorkspaceSettings } from '../../src/types.ts'

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

test('the Advanced tab shows only with the switch on, and search still finds it', () => {
  assert.ok(!availableTabs(true).some((tab) => tab.id === 'advanced'))
  assert.equal(availableTabs(true, false, true).at(-1)?.id, 'advanced')
  // Drafting prompts were editable before a companion existed, so Advanced is too.
  assert.deepEqual(availableTabs(false, false, true).map((tab) => tab.id), ['models', 'advanced'])
  assert.equal(pickTab('advanced', true), 'general')
  assert.equal(pickTab('advanced', true, false, true), 'advanced')
  const found = searchSettings('prompt', true)
  assert.deepEqual(found.map((match) => match.section.heading), ['prompts-heading'])
  assert.ok(found[0].tab.advanced)
})

test('the advanced switch is remembered by the browser and off by default', () => {
  const values = new Map<string, string>()
  const store = { getItem: (key: string) => values.get(key) ?? null, setItem: (key: string, value: string) => { values.set(key, value) }, removeItem: (key: string) => { values.delete(key) } }
  assert.equal(readAdvanced(store), false)
  writeAdvanced(store, true)
  assert.equal(readAdvanced(store), true)
  writeAdvanced(store, false)
  assert.equal(readAdvanced(store), false)
  assert.equal(readAdvanced(undefined), false)
  const broken = { getItem: () => { throw new Error('blocked') }, setItem: () => { throw new Error('blocked') }, removeItem: () => { throw new Error('blocked') } }
  assert.equal(readAdvanced(broken), false)
  writeAdvanced(broken, true)
})

test('prompts are grouped in order and their placeholders explained', () => {
  const prompt = (name: string, group: string, placeholders: string[] = [], help: Record<string, string> = {}) =>
    ({ name, group, label: name, description: '', text: '', default: '', customized: false, outdated: false, placeholders, placeholder_help: help })
  const groups = groupPrompts([prompt('a', 'Chat and life'), prompt('b', 'Character drafting'), prompt('c', 'Chat and life')])
  assert.deepEqual(groups.map(([group, items]) => [group, items.map((item) => item.name)]), [['Chat and life', ['a', 'c']], ['Character drafting', ['b']]])
  assert.equal(placeholderHint(prompt('x', 'g', ['name', 'reason'], { name: "the companion's name" })), "Must keep: {{name}} (the companion's name), {{reason}}.")
  assert.equal(placeholderHint(prompt('x', 'g')), '')
})

test('everything that dials realism down is on the Realism tab, and search finds it there', () => {
  const tab = (query: string) => searchSettings(query, true).map((match) => match.tab.id)
  assert.equal(availableTabs(true).findIndex((item) => item.id === 'realism'), availableTabs(true).findIndex((item) => item.id === 'life') + 1)
  for (const query of ['never closer than', 'closeness', 'cooling', 'hidden values', 'moods', 'odds', 'paced replies', 'drama', 'off plan', 'realism']) {
    assert.ok(tab(query).length && tab(query).every((id) => id === 'realism'), query)
  }
  assert.equal(pickTab('realism', true), 'realism')
})

test('realism presets match the settings they set, and a new world starts on real life', async () => {
  const { REALISM_PRESETS, matchPreset } = await import('../../src/features/settings/presetChoices.ts')
  const life = { drama: 1, paced_replies: true, day_shifts: true, on_her_mind: true } as unknown as LifeSettings
  const fresh = {} as WorkspaceSettings
  assert.equal(matchPreset(life, fresh)?.id, 'real')
  for (const preset of REALISM_PRESETS) {
    assert.equal(matchPreset({ ...life, ...preset.life }, { ...fresh, ...preset.shown })?.id, preset.id)
  }
  assert.equal(matchPreset({ ...life, drama: 2 }, fresh), null)
  assert.equal(new Set(REALISM_PRESETS.map((preset) => preset.label)).size, REALISM_PRESETS.length)
})
