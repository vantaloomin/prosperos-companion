/** Words for Bring your characters and the lore it brings (companion/imports/characters.py, companion/lore.py). */

/** `owner` names the companion whose lore it became, when it is not the world's. */
export interface BroughtBook { id: string; name: string; world: boolean; entries: number; off: number; owner?: string | null }
export interface Brought {
  format: string
  companion: { version: { name: string; definition: { identity: string } } } | null
  book: BroughtBook | null
  picture: boolean
  portrait?: boolean
  /** Why the file's picture was left out, when it had one. */
  picture_note?: string | null
  stepped_back?: string | null
}
/** One condition of an entry's "when" (companion/lore_moments.py): `kind:value`, such as "weather:rain". */
export interface Moment { key: string; label: string }
export interface LoreEntry {
  id: string; title: string; text: string; keywords: string[]; always: boolean; pattern: boolean; enabled: boolean
  /** When the entry also comes up, whatever is said; `when_guessed` when the app read it from its keywords. */
  when: Moment[]; when_guessed: boolean; fits_now: boolean
}
export interface LoreBook {
  id: string; name: string; description: string; source_format: string; source_file: string; world: boolean; enabled: boolean
  /** Lore that comes with the city the companion lives in: it can be switched off but not removed. */
  city: boolean
  created_at: string; entries: LoreEntry[]
}
export type MomentKind = 'weather' | 'season' | 'time' | 'day' | 'holiday' | 'place' | 'work'
export type MomentChoices = Record<MomentKind, Moment[]>
export const MOMENT_KINDS: { kind: MomentKind; label: string }[] = [
  { kind: 'weather', label: 'Weather' }, { kind: 'season', label: 'Season' }, { kind: 'time', label: 'Time of day' },
  { kind: 'day', label: 'Day of the week' }, { kind: 'holiday', label: 'Holiday' }, { kind: 'place', label: 'Place' },
  { kind: 'work', label: 'Work' },
]

export const IMPORT_TYPES = '.png,.json,.charx,.byaf,.lorebook'
/** Above this the server turns a file down (companion/imports/cards.py MAX_SOURCE_BYTES). */
export const MAX_BYTES = 10 * 1024 * 1024

/** A Marinara Engine export carries its sprites and whole gallery as pictures inside the JSON, often past the size
 * limit; only the card and its avatar are used, so the rest is left out before sending. Other files go as they are. */
export async function slimmed(file: File): Promise<Blob> {
  if (file.size <= MAX_BYTES || !/\.json$/i.test(file.name)) return file
  try {
    const value = JSON.parse(await file.text())
    if (typeof value?.type !== 'string' || !value.type.startsWith('marinara_') || !value.data) return file
    delete value.data.sprites
    delete value.data.gallery
    return new Blob([JSON.stringify(value)], { type: 'application/json' })
  } catch {
    return file
  }
}

const entries = (count: number, word = 'entry') => `${count} ${count === 1 ? word : word.replace(/y$/, 'ies')}`

function bookLine(book: BroughtBook): string {
  const off = book.off ? `, ${book.off} of them off` : ''
  return `${entries(book.entries, 'lore entry')}${off}`
}

function bookOnly(book: BroughtBook): string {
  return book.world || !book.owner ? `${book.name} is now part of this world, with ${bookLine(book)}.` : `${book.name} is now ${book.owner}'s lore, with ${bookLine(book)}.`
}

function theirBook(book: BroughtBook, name: string): string {
  if (book.world) return `Their lorebook is now part of this world: ${bookLine(book)}.`
  if (book.owner && book.owner !== name) return `Their lorebook went to ${book.owner}: ${bookLine(book)}.`
  return `Their lorebook came too: ${bookLine(book)}.`
}

/** What an import made, in one or two sentences. */
export function broughtText(result: Brought): string {
  if (!result.companion) return result.book ? bookOnly(result.book) : 'Nothing was imported.'
  const name = result.companion.version.name
  const life = result.companion.version.definition.identity.trim()
  const parts = [`${name} is here (from a ${result.format}).${life ? ` ${life}` : ''}`]
  if (result.book) parts.push(theirBook(result.book, name))
  if (result.picture) parts.push(result.portrait ? 'Their picture is their profile picture.' : 'Their picture is with their reference pictures.')
  else if (result.picture_note) parts.push(result.picture_note)
  if (result.stepped_back) parts.push(`${result.stepped_back} stepped back and keeps everything.`)
  return parts.join(' ')
}

const PHRASES: Record<string, string> = {
  'weather:rain': 'on rainy days', 'weather:snow': 'on snowy days', 'weather:heat': 'on hot days', 'weather:fog': 'on foggy days',
  'time:morning': 'in the morning', 'time:afternoon': 'in the afternoon', 'time:evening': 'in the evening', 'time:night': 'at night',
  'day:weekday': 'on weekdays', 'day:weekend': 'on weekends', 'work:yes': 'at work',
}

function phrase(moment: Moment): string {
  const kind = moment.key.split(':')[0]
  if (PHRASES[moment.key]) return PHRASES[moment.key]
  if (kind === 'season') return `in ${moment.label.toLowerCase()}`
  return kind === 'holiday' || kind === 'place' ? `${kind === 'holiday' ? 'on' : 'in'} ${moment.label}` : moment.label
}

/** "a", "a or b", "a, b or c". */
function alternatives(items: string[]): string {
  return items.length < 3 ? items.join(' or ') : `${items.slice(0, -1).join(', ')} or ${items[items.length - 1]}`
}

/** One kind's phrases, sharing their opening word once: "in fall, winter or spring". */
function oneKind(phrases: string[]): string {
  const lead = phrases[0].split(' ')[0]
  const shared = phrases.length > 1 && phrases.every((item) => item.startsWith(`${lead} `))
  return alternatives(shared ? phrases.map((item, index) => (index ? item.slice(lead.length + 1) : item)) : phrases)
}

/** An entry's "when" in words: one kind or another ("on rainy days or snowy days"), and every kind it names. */
export function momentText(when: Moment[]): string {
  const kinds = new Map<string, string[]>()
  for (const moment of when) {
    const kind = moment.key.split(':')[0]
    kinds.set(kind, [...(kinds.get(kind) ?? []), phrase(moment)])
  }
  return [...kinds.values()].map(oneKind).join(', ')
}

/** When an entry joins a reply. */
export function entryWhen(entry: LoreEntry): string {
  if (entry.pattern) return 'Uses a search pattern the Companion cannot match, so it stays off'
  if (entry.always) return 'Always'
  const moment = momentText(entry.when ?? [])
  if (!entry.keywords.length) return moment ? `${moment[0].toUpperCase()}${moment.slice(1)}` : 'Never: it has no words or moment'
  const words = `When someone mentions ${entry.keywords.slice(0, 6).map((word) => `"${word}"`).join(', ')}${entry.keywords.length > 6 ? '…' : ''}`
  return moment ? `${words}. Also ${moment}` : words
}

export function bookSummary(book: LoreBook): string {
  const on = book.entries.filter((entry) => entry.enabled).length
  const whose = book.city ? 'Comes with the city' : book.world ? 'Everyone in this world' : 'This companion'
  return `${whose} · ${on} of ${entries(book.entries.length)} on${book.city ? '' : ` · ${book.source_format}`}`
}
