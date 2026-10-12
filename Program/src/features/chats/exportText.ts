/** What a chat or the story is exported as (companion/export.py): one HTML page with its pictures, or plain Markdown. */
export type ExportFormat = 'html' | 'md'

/** A chat by its thread id (a companion's timeline on screen, or a group's id), or the story. */
export type ExportTarget = { kind: 'chat'; threadId: string } | { kind: 'story' }

export const EXPORT_FORMATS: { format: ExportFormat; label: string }[] = [
  { format: 'html', label: 'Export as HTML' },
  { format: 'md', label: 'Export as Markdown' },
]

/** The download link: a plain GET that the server answers with the file, so it works on a phone too. */
export function exportHref(target: ExportTarget, format: ExportFormat): string {
  const path = target.kind === 'story' ? '/api/export/story' : `/api/export/chat/${encodeURIComponent(target.threadId)}`
  return `${path}?format=${format}`
}
