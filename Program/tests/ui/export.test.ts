import assert from 'node:assert/strict'
import { test } from 'node:test'
import { EXPORT_FORMATS, exportHref } from '../../src/features/chats/exportText.ts'

test('a chat or the story exports through a plain download link', () => {
  assert.equal(exportHref({ kind: 'chat', threadId: 'abc 1' }, 'html'), '/api/export/chat/abc%201?format=html')
  assert.equal(exportHref({ kind: 'story' }, 'md'), '/api/export/story?format=md')
  assert.deepEqual(EXPORT_FORMATS.map((item) => item.label), ['Export as HTML', 'Export as Markdown'])
})
