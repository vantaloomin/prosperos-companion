/** Words for Bring your characters and the lore it brings (companion/imports/characters.py, companion/lore.py). */

export interface BroughtBook { id: string; name: string; world: boolean; entries: number; off: number }
export interface Brought {
  format: string
  companion: { version: { name: string; definition: { identity: string } } } | null
  book: BroughtBook | null
  picture: boolean
  stepped_back?: string | null
}
export interface LoreEntry { id: string; title: string; text: string; keywords: string[]; always: boolean; pattern: boolean; enabled: boolean }
export interface LoreBook {
  id: string; name: string; description: string; source_format: string; source_file: string; world: boolean; enabled: boolean
  created_at: string; entries: LoreEntry[]
}

export const IMPORT_TYPES = '.png,.json,.charx,.byaf,.lorebook'

const entries = (count: number, word = 'entry') => `${count} ${count === 1 ? word : word.replace(/y$/, 'ies')}`

function bookLine(book: BroughtBook): string {
  const off = book.off ? `, ${book.off} of them off` : ''
  return `${entries(book.entries, 'lore entry')}${off}`
}

/** What an import made, in one or two sentences. */
export function broughtText(result: Brought): string {
  if (!result.companion) {
    return result.book ? `${result.book.name} is now part of this world: ${bookLine(result.book)}.` : 'Nothing was imported.'
  }
  const name = result.companion.version.name
  const life = result.companion.version.definition.identity.trim()
  const parts = [`${name} is here (from a ${result.format}).${life ? ` ${life}` : ''}`]
  if (result.book) parts.push(`Their lorebook came too: ${bookLine(result.book)}.`)
  if (result.picture) parts.push('Their picture is with their reference pictures.')
  if (result.stepped_back) parts.push(`${result.stepped_back} stepped back and keeps everything.`)
  return parts.join(' ')
}

/** When an entry joins a reply. */
export function entryWhen(entry: LoreEntry): string {
  if (entry.pattern) return 'Uses a search pattern the Companion cannot match, so it stays off'
  if (entry.always) return 'Always'
  return `When someone mentions ${entry.keywords.slice(0, 6).join(', ')}${entry.keywords.length > 6 ? '…' : ''}`
}

export function bookSummary(book: LoreBook): string {
  const on = book.entries.filter((entry) => entry.enabled).length
  const whose = book.world ? 'Everyone in this world' : 'This companion'
  return `${whose} · ${on} of ${entries(book.entries.length)} on · ${book.source_format}`
}
