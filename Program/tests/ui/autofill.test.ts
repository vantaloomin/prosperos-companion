import assert from 'node:assert/strict'
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { test } from 'node:test'

// Not text: the browser offers no past entries for these.
const NOT_TEXT = /\btype="(?:checkbox|radio|range|file|color|number|date|time|datetime-local|hidden|password)"/

function sources(folder: string): string[] {
  return readdirSync(folder, { withFileTypes: true }).flatMap((entry) => {
    const path = join(folder, entry.name)
    return entry.isDirectory() ? sources(path) : path.endsWith('.tsx') ? [path] : []
  })
}

test("every text box keeps the browser's past entries out, so words typed for someone else never turn up in it", () => {
  const open: string[] = []
  for (const path of sources('src')) {
    const text = readFileSync(path, 'utf8')
    for (const match of text.matchAll(/<input\b[\s\S]*?\/>/g)) {
      const tag = match[0]
      if (!NOT_TEXT.test(tag) && !/\bautoComplete=/.test(tag)) open.push(`${path}: ${tag.slice(0, 80)}`)
    }
  }
  assert.deepEqual(open, [])
})
