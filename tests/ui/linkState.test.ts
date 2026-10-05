import assert from 'node:assert/strict'
import { test } from 'node:test'
import { hasLink, linkNotes } from '../../src/features/conversation/linkState.ts'
import { observationSummary, sourcesFor } from '../../src/features/settings/contextTools.ts'
import type { Observation } from '../../src/types.ts'

const base: Observation = {
  id: 'o1', service_id: null, service_name: 'This computer (link reader)', category: 'link', purpose: 'conversation', tool: 'read_link',
  arguments: { url: 'https://www.reddit.com/r/baltimore/comments/abc/x/' }, destination: 'www.reddit.com',
  location: { label: 'www.reddit.com', whose: 'user', url: 'https://www.reddit.com/r/baltimore/comments/abc/x/' },
  status: 'failed', content: '', error_code: 'refused', error: 'The site refused to show the page (HTTP 403).', attempts: 1,
  requested_at: '2026-10-05T14:00:00Z', retrieved_at: null, fresh_until: null, fresh: false,
}

test('only messages with a web link ask which links were opened', () => {
  assert.equal(hasLink('see https://example.com/a'), true)
  assert.equal(hasLink('see example.com'), false)
})

test('each link gets a plain note with the real reason it did not load', () => {
  const read: Observation = { ...base, id: 'o2', status: 'ok', error: null, service_id: 's1', arguments: { urls: ['https://app.example/story'] }, location: { label: 'app.example', whose: 'user', url: 'https://app.example/story' } }
  const weather: Observation = { ...base, id: 'o3', category: 'weather' }
  assert.deepEqual(linkNotes([base, read, weather]), [
    { id: 'o1', host: 'reddit.com', read: false, reason: 'The site refused to show the page (HTTP 403).' },
    { id: 'o2', host: 'app.example', read: true, reason: 'It could not be opened.' },
  ])
})

test('link reading sends only the link, and its records name the link', () => {
  assert.deepEqual(sourcesFor('link'), ['url', 'literal'])
  assert.equal(sourcesFor('news').includes('url'), false)
  assert.equal(observationSummary(base).title, 'Link: https://www.reddit.com/r/baltimore/comments/abc/x/')
})

test('web search sends only what you asked for and says when it runs', async () => {
  const { canTry, purposeLabel, SEARCH_PRESETS } = await import('../../src/features/settings/contextTools.ts')
  assert.deepEqual(sourcesFor('web_search'), ['topic', 'literal'])
  assert.equal(purposeLabel('web_search', 'conversation', 'Mira'), 'When you ask in chat to search or look something up')
  assert.equal(purposeLabel('weather', 'companion_city', 'Mira'), "For Mira's city, when it is a real place")
  assert.equal(canTry('web_search'), false)
  assert.equal(canTry('weather'), true)
  assert.deepEqual(SEARCH_PRESETS.map((preset) => preset.url), ['https://search.parallel.ai/mcp', 'https://mcp.exa.ai/mcp', 'https://mcp.firecrawl.dev/v2/mcp'])
})
