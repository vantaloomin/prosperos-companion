import assert from 'node:assert/strict'
import { mock, test } from 'node:test'
import { followAgainIn, followReply } from '../../src/features/conversation/useReplyStream.ts'
import type { Message } from '../../src/types.ts'

class FakeSource {
  readyState = 1
  closed = false
  onerror: ((event: Event) => void) | null = null
  listeners: Record<string, (event: MessageEvent) => void> = {}
  url: string
  constructor(url: string) { this.url = url }
  addEventListener(name: string, listener: (event: MessageEvent) => void) { this.listeners[name] = listener }
  close() { this.closed = true; this.readyState = 2 }
  send(name: string, data: object) { this.listeners[name]({ data: JSON.stringify(data) } as MessageEvent) }
  giveUp() { this.readyState = 2; this.onerror?.(new Event('error')) }
}

function follow() {
  const sources: FakeSource[] = []
  const seen = { text: [] as string[], done: [] as Message[], lost: 0 }
  const handlers = { onText: (_id: string, text: string) => seen.text.push(text), onPhase: () => {}, onDone: (reply: Message) => seen.done.push(reply), onLost: () => { seen.lost += 1 } }
  const stop = followReply('r1', () => handlers, (url) => { const source = new FakeSource(url); sources.push(source); return source })
  return { sources, seen, stop }
}

test('a reply whose stream was lost is followed again and still shows when it lands', () => {
  mock.timers.enable({ apis: ['setTimeout'] })
  try {
    const { sources, seen } = follow()
    sources[0].send('snapshot', { text: 'Half' })
    sources[0].giveUp()
    assert.equal(seen.lost, 1)
    assert.equal(sources.length, 1)
    mock.timers.tick(followAgainIn(0))
    assert.equal(sources.length, 2)
    assert.equal(sources[1].url, '/api/conversation/replies/r1/events')
    sources[1].send('snapshot', { text: 'Half and' })
    sources[1].send('delta', { text: ' the rest.' })
    sources[1].send('done', { id: 'r1', status: 'complete', text: 'Half and the rest.' })
    assert.deepEqual(seen.text, ['Half', 'Half and', 'Half and the rest.'])
    assert.equal(seen.done.length, 1)
    assert.ok(sources[1].closed)
  } finally { mock.timers.reset() }
})

test('a stream that is only reconnecting by itself, or already done, is left alone', () => {
  mock.timers.enable({ apis: ['setTimeout'] })
  try {
    const { sources, seen } = follow()
    sources[0].readyState = 0
    sources[0].onerror?.(new Event('error'))
    sources[0].send('done', { id: 'r1', status: 'complete', text: 'Hi' })
    sources[0].onerror?.(new Event('error'))
    mock.timers.tick(60000)
    assert.equal(seen.lost, 0)
    assert.equal(sources.length, 1)
  } finally { mock.timers.reset() }
})

test('stopping cancels a follow waiting to start again, and waits grow to a cap', () => {
  mock.timers.enable({ apis: ['setTimeout'] })
  try {
    const { sources, stop } = follow()
    sources[0].giveUp()
    stop()
    mock.timers.tick(60000)
    assert.equal(sources.length, 1)
  } finally { mock.timers.reset() }
  assert.deepEqual([0, 1, 2, 3, 4, 10].map(followAgainIn), [1000, 2000, 4000, 8000, 15000, 15000])
})
