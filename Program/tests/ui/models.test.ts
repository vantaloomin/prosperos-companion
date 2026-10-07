import assert from 'node:assert/strict'
import { test } from 'node:test'
import { applyDiscovered, discoveredSettings, filterModels, profileReady, recallReady, savedKeyApplies, typedModelSettings, type DiscoveredModel } from '../../src/features/settings/models/discovery.ts'
import { jobChoice, recallFallback } from '../../src/features/settings/models/routing.ts'
import { configFor, type ModelsOverview } from '../../src/features/settings/models/types.ts'

const sonnet: DiscoveredModel = { id: 'anthropic/claude-sonnet-5.5', name: 'Claude Sonnet 5.5', context_tokens: 200000, max_output_tokens: 500, limit_source: 'provider', supported_efforts: ['low', 'high'] }
const mystery: DiscoveredModel = { id: 'mystery', name: 'mystery', context_tokens: null, max_output_tokens: null, limit_source: 'unreported' }

test('a chosen model fills reported limits and never raises the reply above them', () => {
  const settings = discoveredSettings(sonnet, configFor('openrouter'))
  assert.equal(settings.context_tokens, 200000)
  assert.equal(settings.max_output_tokens, 500)
  assert.deepEqual(settings.reported_capabilities?.supported_efforts, ['low', 'high'])
})

test('a typed ID forgets reported limits unless it matches a listed model', () => {
  const current = { ...configFor('openrouter'), ...discoveredSettings(sonnet, configFor('openrouter')) }
  assert.equal(typedModelSettings('other', current, [sonnet]).reported_capabilities, null)
  assert.equal(typedModelSettings(sonnet.id, current, [sonnet]).context_tokens, 200000)
})

test('a test picks the only returned model, and otherwise keeps the choice', () => {
  assert.equal(applyDiscovered({ available: true, models: [], model_details: [mystery], generated: false }, configFor('local')).model, 'mystery')
  assert.equal(applyDiscovered({ available: true, models: [], model_details: [mystery, sonnet], generated: false }, configFor('local')).model, '')
})

test('model search matches every word in the name or ID', () => {
  assert.deepEqual(filterModels([sonnet, mystery], 'claude 5.5').map(model => model.id), [sonnet.id])
})

test('readiness and saved keys follow provider and address', () => {
  assert.equal(profileReady(configFor('codex')), false)
  assert.equal(profileReady({ ...configFor('codex'), model: 'gpt-5' }), true)
  const saved = { ...configFor('compatible'), base_url: 'https://one.example/v1' }
  assert.equal(savedKeyApplies(saved, true, { ...saved, model: 'x' }), true)
  assert.equal(savedKeyApplies(saved, true, { ...saved, base_url: 'https://two.example/v1' }), false)
  assert.equal(savedKeyApplies(saved, true, configFor('openai')), false)
})

test('a job without its own profile shows the conversation profile it uses', () => {
  const profile = (id: string, name: string) => ({ id, name, revision: 1, config: configFor('local'), provider_name: 'Local', has_saved_key: false, ready: true })
  const overview: ModelsOverview = { profiles: [profile('a', 'Local'), profile('b', 'Claude')], routes: { chat: 'a', drafting: 'b' }, jobs: [] }
  assert.deepEqual(jobChoice(overview, 'life'), { value: '', inherited: 'Local' })
  assert.deepEqual(jobChoice(overview, 'drafting'), { value: 'b', inherited: null })
  assert.deepEqual(jobChoice(overview, 'chat'), { value: 'a', inherited: null })
})

test('recall without its own profile says whether it borrows the conversation profile or matches keywords', () => {
  const profile = (id: string, embedding: string) => ({ id, name: id, revision: 1, config: { ...configFor('local'), embedding_model: embedding }, provider_name: 'Local', has_saved_key: false, ready: true, recall_ready: !!embedding })
  assert.equal(recallFallback({ profiles: [profile('Chat', '')], routes: { chat: 'Chat' }, jobs: [] }), 'Keywords only')
  assert.equal(recallFallback({ profiles: [profile('Chat', 'nomic')], routes: { chat: 'Chat' }, jobs: [] }), 'Same as conversation (Chat)')
  assert.equal(recallReady({ ...configFor('local'), embedding_model: 'qwen3-embedding' }), true)
  assert.equal(recallReady({ ...configFor('anthropic'), embedding_model: 'x' }), false)
})
