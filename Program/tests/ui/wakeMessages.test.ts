import assert from 'node:assert/strict'
import { test } from 'node:test'
import { inView } from '../../src/features/conversation/useWakeMessages.ts'

const at = (top: number, bottom: number, id = '') => ({ id, getBoundingClientRect: () => ({ top, bottom }) })

test('only the messages showing in the transcript are woken, skipped ones included', () => {
  const messages = [at(-400, -250, 'above'), at(-40, 60, 'cut-top'), at(100, 250, 'middle'), at(380, 530, 'cut-bottom'), at(600, 750, 'below')]
  const transcript = { getBoundingClientRect: () => ({ top: 0, bottom: 400 }), querySelectorAll: () => messages } as unknown as HTMLElement
  assert.deepEqual(inView(transcript).map((message) => message.id), ['cut-top', 'middle', 'cut-bottom'])
})
