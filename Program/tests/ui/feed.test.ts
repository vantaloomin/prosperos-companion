import assert from 'node:assert/strict'
import { test } from 'node:test'
import { ReadBatcher, SEEK_PAGES, askForNew, firstUnread, joinPages, newBelow, nextReaction, seekStep, seenEnough, takeAskForNew } from '../../src/features/feed/feedState.ts'
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

const shown = (id: string, read: boolean) => ({ id, read }) as FeedPost

test('a post counts as seen once half of it, or half the screen of it, was on screen', () => {
  assert.equal(seenEnough(0.5, 200, 800), true)
  assert.equal(seenEnough(0.3, 200, 800), false)
  // A post three screens tall is never half on screen; filling half the screen is enough.
  assert.equal(seenEnough(0.2, 480, 800), true)
  assert.equal(seenEnough(0.1, 240, 800), false)
})

test('a new post below ones already seen is found, page by page if need be', () => {
  const older = [shown('a', true), shown('b', true), shown('c', false)]
  assert.equal(firstUnread(older)?.id, 'c')
  assert.equal(newBelow(older, 1), true)
  assert.equal(newBelow([shown('c', false), shown('a', true)], 1), false)
  assert.equal(newBelow([shown('a', true)], 0), false)
  assert.equal(seekStep(older, 1, true), 'show')
  assert.equal(seekStep([shown('a', true)], 1, true), 'more')
  assert.equal(seekStep([shown('a', true)], 1, false), 'stop')
  assert.equal(seekStep([shown('a', true)], SEEK_PAGES, true), 'stop')
})

test("Today's button asks the feed once", () => {
  assert.equal(takeAskForNew(), false)
  askForNew()
  assert.equal(takeAskForNew(), true)
  assert.equal(takeAskForNew(), false)
})
