import assert from 'node:assert/strict'
import { test } from 'node:test'
import { loadBack, snippet, turnOf } from '../../src/features/conversation/search.ts'
import type { Message, SearchResult } from '../../src/types.ts'

test('a snippet keeps the original case of the match and trims at word boundaries', () => {
  const text = 'We walked for a long while along the old seawall before reaching the Harbour market at dusk, which was closing.'
  const result = snippet(text, 'harbour', 20)
  assert.equal(result.match, 'Harbour')
  assert.equal(result.before, '…before reaching the ')
  assert.equal(result.after, ' market at dusk,…')
})

test('a short message is shown whole', () => {
  assert.deepEqual(snippet('See you at\nthe harbour', 'HARBOUR'), { before: 'See you at the ', match: 'harbour', after: '' })
})

test('a match the browser cannot locate falls back to the opening', () => {
  assert.deepEqual(snippet('Die Straße', 'strasse'), { before: '', match: '', after: 'Die Straße' })
})

test('a reply result jumps to the turn it answers', () => {
  const base: SearchResult = { id: 'r', seq: 2, role: 'companion', text: 'x', status: 'complete', reply_to: 'u', created_at: '' }
  assert.equal(turnOf(base), 'u')
  assert.equal(turnOf({ ...base, role: 'user', reply_to: null }), 'r')
})

test('jumping back loads every page the result needs and hands them over together', async () => {
  const all = Array.from({ length: 1200 }, (_, index) => ({ id: `m${index + 1}`, seq: index + 1 }) as Message)
  const asked: number[] = []
  const fetchPage = async (before: number) => { asked.push(before); return all.filter((item) => item.seq < before).slice(-500) }
  const found = await loadBack(1101, 150, 500, fetchPage)
  assert.deepEqual(asked, [1101, 601])
  assert.equal(found.messages.length, 1000)
  assert.equal(found.exhausted, false)
  const rest = await loadBack(101, 5, 500, fetchPage)
  assert.equal(rest.messages.length, 100)
  assert.equal(rest.exhausted, true)
  assert.deepEqual(await loadBack(undefined, 5, 500, fetchPage), { messages: [], exhausted: false })
})
