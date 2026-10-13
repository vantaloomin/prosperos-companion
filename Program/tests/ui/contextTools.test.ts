import assert from 'node:assert/strict'
import { test } from 'node:test'
import { argumentKind, canSave, initialMapping, propertyLabel, withAppFilled, withPurpose, withSource, missingArguments, observationSummary, sentArguments, serviceBody, sourcesFor } from '../../src/features/settings/contextTools.ts'
import type { ContextTool, Observation } from '../../src/types.ts'

test('a stdio service sends the program and one argument per line', () => {
  const body = serviceBody({ name: ' Weather ', transport: 'stdio', program: ' uvx ', args: 'weather-mcp\n\n --metric ', url: 'ignored', secret: '', secretName: 'WEATHER_KEY' })
  assert.deepEqual(body, { name: 'Weather', transport: 'stdio', secret: undefined, secret_name: 'WEATHER_KEY', command: ['uvx', 'weather-mcp', '--metric'] })
  const http = serviceBody({ name: 'Events', transport: 'http', program: '', args: '', url: ' https://x.test/mcp ', secret: 'k', secretName: '' })
  assert.deepEqual(http, { name: 'Events', transport: 'http', secret: 'k', secret_name: '', url: 'https://x.test/mcp' })
})

const tool: ContextTool = { name: 'get_forecast', description: '', read_only: true, input_schema: { properties: { location: {}, units: {} }, required: ['location', 'units'] } }

test('mappings start from what is saved, then the suggestion', () => {
  assert.deepEqual(initialMapping([tool], undefined, { tool: 'get_forecast', arguments: { location: { source: 'place' } }, missing: ['units'] }),
    { tool: 'get_forecast', arguments: { location: { source: 'place' } }, run_in: ['conversation'] })
  assert.deepEqual(initialMapping([tool]), { tool: 'get_forecast', arguments: {}, run_in: ['conversation'] })
  assert.deepEqual(missingArguments(tool, { location: { source: 'place' }, units: { source: 'literal', value: '' } }), ['units'])
  assert.deepEqual(missingArguments(tool, { location: { source: 'place' }, units: { source: 'literal', value: 'metric' } }), [])
  assert.ok(!sourcesFor('weather').includes('topic'))
  assert.ok(sourcesFor('news').includes('topic'))
})

const base: Observation = {
  id: 'o1', service_id: 's1', service_name: 'Stand-in', category: 'weather', purpose: 'conversation', tool: 'get_forecast',
  arguments: { location: 'Baltimore, MD' }, destination: 'Local program: x', location: { label: 'Baltimore, MD', whose: 'user' },
  status: 'ok', content: 'Rain', error_code: null, error: null, attempts: 1, requested_at: '2026-10-05T12:00:00+00:00',
  retrieved_at: '2026-10-05T12:00:00+00:00', fresh_until: '2026-10-05T13:00:00+00:00', fresh: true,
}

test('lookups say whether they still count as current', () => {
  const now = new Date('2026-10-05T12:30:00Z')
  assert.equal(observationSummary(base, now).tone, 'ok')
  assert.equal(observationSummary(base, now).title, 'Weather for Baltimore, MD')
  assert.equal(observationSummary(base, new Date('2026-10-05T14:00:00Z')).tone, 'stale')
  const failed = observationSummary({ ...base, status: 'failed', error: 'The tool did not answer in time.' }, now)
  assert.deepEqual([failed.tone, failed.state], ['failed', 'Failed: The tool did not answer in time.'])
  const city = observationSummary({ ...base, location: { label: 'Miami, Florida', whose: 'companion' } }, now)
  assert.equal(city.title, "Weather for Miami, Florida (the companion's city)")
  assert.equal(sentArguments(base), 'location: Baltimore, MD')
  assert.equal(sentArguments({ ...base, arguments: {} }), 'nothing')
})

test('drafts change one property or timing at a time', () => {
  const draft = { tool: 'get_forecast', arguments: {}, run_in: ['conversation' as const] }
  const placed = withSource(withSource(draft, 'location', 'place'), 'units', 'literal')
  assert.deepEqual(placed.arguments, { location: { source: 'place' }, units: { source: 'literal', value: '' } })
  assert.equal(canSave(placed, tool), false)
  assert.equal(canSave(withSource(placed, 'units', '') , { ...tool, input_schema: { required: ['location'] } }), true)
  assert.deepEqual(withPurpose(draft, 'companion_city', true).run_in, ['conversation', 'companion_city'])
  assert.equal(canSave(withPurpose(placed, 'conversation', false), tool), false)
})

test('tool arguments read as words and are offered by their type', () => {
  assert.equal(propertyLabel('allow_live_fetch'), 'Allow live fetch')
  assert.equal(propertyLabel('maxResults'), 'Max results')
  assert.equal(propertyLabel('urls'), 'URLs')
  assert.equal(propertyLabel('request_id'), 'Request ID')
  assert.equal(argumentKind('session_id', { type: 'string' }), 'app')
  assert.equal(argumentKind('allow_live_fetch', { type: 'boolean' }), 'boolean')
  assert.equal(argumentKind('mode', { type: 'string', enum: ['fast', 'deep'] }), 'choice')
  assert.equal(argumentKind('max_results', { type: ['integer', 'null'] }), 'number')
  assert.equal(argumentKind('objective', { type: 'string' }), 'text')
  const search: ContextTool = { name: 'web_search', description: '', read_only: true, input_schema: { properties: { objective: {}, session_id: { type: 'string' } } } }
  const filled = withAppFilled({ tool: 'web_search', arguments: { objective: { source: 'topic' } }, run_in: ['conversation'] }, search)
  assert.deepEqual(filled.arguments, { objective: { source: 'topic' }, session_id: { source: 'session' } })
  assert.equal(withAppFilled(filled, search), filled)
})
