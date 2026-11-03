import assert from 'node:assert/strict'
import { test } from 'node:test'
import { SETTINGS_TABS, availableTabs, pickTab, searchSettings } from '../../src/features/settings/sections.ts'
import { groupPrompts, placeholderHint } from '../../src/features/settings/prompts.ts'
import { setupSteps } from '../../src/features/conversation/setup.ts'
import type { Companion, LifeSettings, WorkspaceSettings } from '../../src/types.ts'

test('a deep link opens its tab, and an unknown or unavailable one opens the first', () => {
  assert.equal(pickTab('pictures', true), 'pictures')
  // Tabs from before 1.3 open the group that holds them now.
  assert.equal(pickTab('images', true), 'pictures')
  assert.equal(pickTab('life', true), 'world')
  assert.equal(pickTab('lookups', true), 'world')
  assert.equal(pickTab('phone', true), 'devices')
  assert.equal(pickTab('debug', true), 'data')
  assert.equal(pickTab('debug', true, true), 'general')
  assert.deepEqual(availableTabs(true).map((tab) => tab.id), ['general', 'models', 'realism', 'world', 'memory', 'pictures', 'devices', 'data', 'advanced'])
  assert.equal(pickTab(undefined, true), 'general')
  assert.equal(pickTab('nonsense', true), 'general')
  // Before a companion exists only the model settings can be changed.
  assert.equal(pickTab('images', false), 'models')
  assert.deepEqual(availableTabs(false).map((tab) => tab.id), ['models', 'advanced'])
})

test('search finds sections by title, tab name or keyword, needing every word', () => {
  const found = (query: string, hasCompanion = true) => searchSettings(query, hasCompanion).map((match) => match.section.heading)
  assert.deepEqual(found('timezone'), ['time-heading'])
  assert.deepEqual(found('WEATHER'), ['context-heading'])
  assert.deepEqual(found('restore'), ['backup-heading'])
  assert.deepEqual(found('full logging'), ['model-calls-heading'])
  assert.deepEqual(searchSettings('logging', true, true), [])
  assert.ok(found('quiet hours').includes('notifications-heading'))
  assert.deepEqual(found('anthropic key'), ['models-heading'])
  assert.deepEqual(found('weather', false), [])
  assert.deepEqual(found('   '), [])
  // Rough patches sit beside Breaks and breakups, which need them (Iris).
  assert.deepEqual(found('rough patches'), ['love-heading'])
  assert.deepEqual(found('breakups'), ['love-heading'])
})

test('every section heading is listed once', () => {
  const headings = SETTINGS_TABS.flatMap((tab) => tab.sections.map((section) => section.heading))
  assert.equal(new Set(headings).size, headings.length)
})

test('the setup checklist sends you straight to the Models tab', () => {
  const companion = { version: { name: 'Mira', definition: { home_city: '', schedule: [] } } } as unknown as Companion
  assert.equal(setupSteps(companion, null).find((step) => step.id === 'connection')?.view, 'settings/models')
})

test('Advanced is always listed, last, and search finds it', () => {
  assert.equal(availableTabs(true).at(-1)?.id, 'advanced')
  assert.equal(pickTab('advanced', true), 'advanced')
  const found = searchSettings('prompt', true)
  assert.deepEqual(found.map((match) => match.section.heading), ['prompts-heading'])
  assert.ok(found[0].tab.advanced)
})

test('prompts are grouped in order and their placeholders explained', () => {
  const prompt = (name: string, group: string, placeholders: string[] = [], help: Record<string, string> = {}) =>
    ({ name, group, label: name, description: '', text: '', default: '', customized: false, outdated: false, placeholders, placeholder_help: help, lines: false, more: false })
  const groups = groupPrompts([prompt('a', 'Chat and life'), prompt('b', 'Character drafting'), prompt('c', 'Chat and life')])
  assert.deepEqual(groups.map(([group, items]) => [group, items.map((item) => item.name)]), [['Chat and life', ['a', 'c']], ['Character drafting', ['b']]])
  assert.equal(placeholderHint(prompt('x', 'g', ['name', 'reason'], { name: "the companion's name" })), "Must keep: {{name}} (the companion's name), {{reason}}.")
  assert.equal(placeholderHint(prompt('x', 'g')), '')
  const list = { ...prompt('y', 'Pictures', ['possessive'], { possessive: 'her, his or their' }), lines: true }
  assert.equal(placeholderHint(list), 'One line each: a name, a colon, then its words. Keep every name; words can be left empty. A line can use {{possessive}} (her, his or their).')
  assert.equal(placeholderHint({ ...prompt('m', 'Pictures'), lines: true, more: true }), 'One line each: a name, a colon, then its words. Keep every name and add your own; words can be left empty.')
  assert.equal(placeholderHint({ ...prompt('z', 'Pictures'), lines: true }), 'One line each: a name, a colon, then its words. Keep every name; words can be left empty.')
})

test('everything that dials realism down is on the Realism tab, and search finds it there', () => {
  const tab = (query: string) => searchSettings(query, true).map((match) => match.tab.id)
  assert.equal(availableTabs(true).findIndex((item) => item.id === 'realism'), availableTabs(true).findIndex((item) => item.id === 'models') + 1)
  // Drama is each world's own (companion/life/world_drama.py), set on Realism in that world.
  const drama = searchSettings('drama', true).map((match) => match.section.heading)
  assert.ok(drama.includes('pace-heading') && !drama.includes('world-life-heading'))
  for (const query of ['never closer than', 'closeness', 'cooling', 'hidden values', 'moods', 'odds', 'paced replies', 'off plan', 'realism', 'haircut', 'hair colour', 'pets', 'vet', 'life admin', 'guests', 'retirement', 'mortgage', 'moving on']) {
    assert.ok(tab(query).length && tab(query).every((id) => id === 'realism'), query)
  }
  assert.equal(pickTab('realism', true), 'realism')
})

test('realism presets match the settings they set, and a new world starts on real life', async () => {
  const { REALISM_PRESETS, matchPreset } = await import('../../src/features/settings/presetChoices.ts')
  const life = { drama: 1, paced_replies: true, day_shifts: true, on_her_mind: true, upkeep_realism: 2, kitchen_realism: 2, looks_realism: 2, pets_realism: 2, pets_can_die: true, admin_realism: 2, work_realism: 2, guests_realism: 2, media_realism: 2, memes_realism: 2, hobbies_realism: 2, together_realism: 2, onward_realism: 2, rough_patches_realism: 2, steps_pace: 2, friends_fall: true, breakups: true, love_life: 2, life_turns: 2, growing_families: 2, family_life: 2, family_shapes: 2, people_pass_away: false, loss: 2, politics_realism: 2, trolls_realism: 1, inner_voice: 2, their_look: 2, waking_realism: 2, read_pace: 2 } as unknown as LifeSettings
  const fresh = {} as WorkspaceSettings
  assert.equal(matchPreset(life, fresh)?.id, 'real')
  for (const preset of REALISM_PRESETS) {
    assert.equal(matchPreset({ ...life, ...preset.life }, { ...fresh, ...preset.shown })?.id, preset.id)
  }
  assert.equal(matchPreset({ ...life, drama: 2 }, fresh), null)
  assert.equal(matchPreset({ ...life, pets_can_die: false }, fresh), null)
  assert.equal(new Set(REALISM_PRESETS.map((preset) => preset.label)).size, REALISM_PRESETS.length)
  // The Loss slider (People can pass away stays off): rare on an easy life, often with the drama (v0.15).
  assert.deepEqual(REALISM_PRESETS.map((preset) => [preset.id, preset.life.loss, preset.life.people_pass_away]), [['real', 2, false], ['drama', 3, false], ['easy', 0, false], ['strings', 2, false]])
  // Local politics: true to life on real life, quiet on an easy one, lively with the drama.
  assert.deepEqual(REALISM_PRESETS.map((preset) => [preset.id, preset.life.politics_realism]), [['real', 2], ['drama', 3], ['easy', 1], ['strings', 2]])
  // Trolls and snark on posts: rivals only on real life, off on an easy one, trolls with the drama.
  assert.deepEqual(REALISM_PRESETS.map((preset) => [preset.id, preset.life.trolls_realism]), [['real', 1], ['drama', 3], ['easy', 0], ['strings', 1]])
  // Inner voice (Observer mode, v0.16): true to life on real life, a few thoughts on an easy one.
  assert.deepEqual(REALISM_PRESETS.map((preset) => [preset.id, preset.life.inner_voice]), [['real', 2], ['drama', 3], ['easy', 1], ['strings', 3]])
})

test('your own mix names the preset it is closest to', async () => {
  const { nearestPreset } = await import('../../src/features/settings/presetChoices.ts')
  const life = { drama: 3, paced_replies: false, day_shifts: true, on_her_mind: true, upkeep_realism: 3, looks_realism: 3 } as unknown as LifeSettings
  assert.equal(nearestPreset(life, {} as WorkspaceSettings).id, 'drama')
  assert.equal(nearestPreset({ ...life, drama: 0, day_shifts: false }, {} as WorkspaceSettings).id, 'easy')
})

test('the People can pass away hint says who grieves and that a partner never dies (v0.15)', async () => {
  const { PASS_AWAY_HINT } = await import('../../src/features/character/lossText.ts')
  assert.match(PASS_AWAY_HINT, /The companion grieves for weeks/)
  assert.match(PASS_AWAY_HINT, /never a partner/)
})
