import assert from 'node:assert/strict'
import { test } from 'node:test'
import { ReadBatcher, joinPages, nextReaction } from '../../src/features/feed/feedState.ts'
import type { FeedPost } from '../../src/types.ts'

const post = (id: string) => ({ id }) as FeedPost

test('pages join without repeats', () => {
  assert.deepEqual(joinPages([{ posts: [post('a'), post('b')], next_before: 'x', unread: 0 }, { posts: [post('b'), post('c')], next_before: null, unread: 0 }]).map((item) => item.id), ['a', 'b', 'c'])
})

test('choosing the current reaction clears it', () => {
  assert.equal(nextReaction('heart', 'heart'), null)
  assert.equal(nextReaction('heart', 'hug'), 'hug')
})

test('seen posts are sent once, in one batch', () => {
  const sent: string[][] = []
  const batcher = new ReadBatcher((ids) => sent.push(ids), 10_000)
  batcher.saw('a')
  batcher.saw('b')
  batcher.saw('a')
  batcher.flush()
  batcher.flush()
  assert.deepEqual(sent, [['a', 'b']])
})
