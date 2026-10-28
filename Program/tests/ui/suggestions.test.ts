import assert from 'node:assert/strict'
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { test } from 'node:test'
import { suggestionsFor } from '../../src/components/suggestions.ts'

const WORDS = ['friend', 'close friend', 'best friend', 'mom', 'dad', 'sister']

test('suggestions put words starting with what is typed first, then ones containing it', () => {
  assert.deepEqual(suggestionsFor(WORDS, 'fr'), ['friend', 'close friend', 'best friend'])
  assert.deepEqual(suggestionsFor(WORDS, 'S'), ['sister', 'close friend', 'best friend'])
  assert.deepEqual(suggestionsFor(WORDS, 'aunt'), [])
})

test('an empty box, or one already holding a word, offers every word', () => {
  assert.deepEqual(suggestionsFor(WORDS, ''), WORDS)
  assert.deepEqual(suggestionsFor(WORDS, 'Mom '), WORDS)
})

function sources(folder: string): string[] {
  return readdirSync(folder, { withFileTypes: true }).flatMap((entry) => {
    const path = join(folder, entry.name)
    return entry.isDirectory() ? sources(path) : path.endsWith('.tsx') ? [path] : []
  })
}

test("text boxes offer the app's own suggestion list, never the browser's datalist popup (slider ticks are fine)", () => {
  const popups: string[] = []
  for (const path of sources('src')) {
    for (const match of readFileSync(path, 'utf8').matchAll(/<input\b[\s\S]*?\/>/g)) {
      if (/\blist=/.test(match[0]) && !/type="range"/.test(match[0])) popups.push(`${path}: ${match[0].slice(0, 80)}`)
    }
  }
  assert.deepEqual(popups, [])
})
