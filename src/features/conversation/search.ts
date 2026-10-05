import type { SearchResult } from '../../types'

export interface Snippet { before: string; match: string; after: string }

/** The words around the first match, trimmed at word boundaries. Falls back to the opening when case folding moved the match. */
export function snippet(text: string, query: string, radius = 70): Snippet {
  const needle = query.trim()
  const start = needle ? text.toLocaleLowerCase().indexOf(needle.toLocaleLowerCase()) : -1
  if (start < 0) return { before: '', match: '', after: clip(text, radius * 2, 'end') }
  return {
    before: clip(text.slice(0, start), radius, 'start'),
    match: text.slice(start, start + needle.length),
    after: clip(text.slice(start + needle.length), radius, 'end'),
  }
}

function clip(text: string, length: number, keep: 'start' | 'end'): string {
  const flat = text.replace(/\s+/g, ' ')
  if (flat.length <= length) return flat
  // Drop a word the cut landed inside, but never one that was cut cleanly.
  if (keep === 'end') {
    const head = flat.slice(0, length)
    return `${/\s/.test(flat[length]) ? head : head.replace(/\s\S*$/, '')}…`
  }
  const tail = flat.slice(-length)
  return `…${/\s/.test(flat[flat.length - length - 1]) ? tail : tail.replace(/^\S*\s/, '')}`
}

/** The turn a result belongs to: a user message is its own turn, a reply sits under the message it answers. */
export function turnOf(result: SearchResult): string {
  return result.role === 'user' || !result.reply_to ? result.id : result.reply_to
}
