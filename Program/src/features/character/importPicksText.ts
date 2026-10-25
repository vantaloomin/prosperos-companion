/** Choosing what to import from a file (companion/imports/characters.py `inspect`, companion/world/marinara.py):
 * what the file holds, and which parts are ticked. Everything starts ticked, so one click imports it all. */

export interface PreviewEntry { title: string; keywords: string[]; always: boolean; enabled: boolean; pattern: boolean; text: string }
export interface PreviewBook { name: string; format: string; entries: PreviewEntry[] }
export interface Member { id: string; name: string }
/** A character or lorebook file. `already` is the companion the character already is. */
export interface CharacterFile {
  kind: 'character'
  format: string
  character: { name: string; about: string; more_about: boolean } | null
  picture: { usable: boolean; note: string | null; portrait: boolean } | null
  book: PreviewBook | null
  unused: string[]
  companions: Member[]
  already: Member | null
}
/** A Marinara world map. `already` names the city it came in as before. */
export interface MapFile {
  kind: 'map'
  format: string
  city: { name: string; counts: { neighborhoods: number; places: number; employers: number } }
  book: PreviewBook | null
  already: string | null
}
export type FileContents = CharacterFile | MapFile

export interface Picks {
  /** The character, or the world map's city. */
  main: boolean
  picture: boolean
  book: boolean
  /** Positions of the ticked lorebook entries. */
  entries: Set<number>
  /** '' for the app's choice, 'new', 'world' or a companion's id. */
  loreFor: string
}

/** Everything ticked, except a character who is already here or a city that already came in. */
export function startingPicks(found: FileContents): Picks {
  const main = found.kind === 'map' ? !found.already : found.character !== null && !found.already
  return { main, picture: true, book: true, entries: new Set(found.book?.entries.map((_, index) => index) ?? []), loreFor: '' }
}

/** Whose the lorebook can become, in the order offered, and the one the app picks. */
export function owners(found: CharacterFile, picks: Picks): { options: { value: string; label: string }[]; chosen: string } {
  const bringing = found.character !== null && picks.main
  const options = [
    ...(bringing ? [{ value: 'new', label: found.character?.name || 'The new character' }] : []),
    ...found.companions.map((member) => ({ value: member.id, label: member.name })),
    { value: 'world', label: 'Everyone in this world' },
  ]
  const fallback = bringing ? 'new' : found.already?.id ?? 'world'
  const chosen = options.some((option) => option.value === picks.loreFor) ? picks.loreFor : fallback
  return { options, chosen }
}

/** Whether anything is ticked at all. */
export function anythingTicked(found: FileContents, picks: Picks): boolean {
  return (picks.main && (found.kind === 'map' ? !found.already : found.character !== null)) || (picks.book && picks.entries.size > 0 && !!found.book)
}

/** The request body's picks. Every entry ticked is sent as "all". */
export function pickBody(found: FileContents, picks: Picks) {
  const total = found.book?.entries.length ?? 0
  const entries = picks.entries.size === total ? null : [...picks.entries].sort((a, b) => a - b)
  if (found.kind === 'map') return { city: picks.main && !found.already, book: picks.book, entries }
  return { character: picks.main, picture: picks.picture, book: picks.book, entries, lore_for: owners(found, picks).chosen }
}

export function entryCount(picks: Picks, book: PreviewBook): string {
  const total = book.entries.length
  const word = total === 1 ? 'entry' : 'entries'
  return picks.entries.size === total ? `All ${total} ${word}` : `${picks.entries.size} of ${total} ${word}`
}

/** When an entry joins a reply, shortly. */
export function entryHint(entry: PreviewEntry): string {
  if (entry.pattern) return 'Uses a search pattern, so it comes in off'
  const when = entry.always ? 'Always on' : entry.keywords.length ? `When someone mentions ${entry.keywords.map((word) => `"${word}"`).join(', ')}` : 'No words to come up on'
  return entry.enabled ? when : `${when}. Off in the file, so it comes in off`
}

export function mapCounts(found: MapFile): string {
  const { neighborhoods, places } = found.city.counts
  const plural = (count: number, word: string) => `${count} ${word}${count === 1 ? '' : 's'}`
  return `${plural(neighborhoods, 'neighborhood')} and ${plural(places, 'place')}`
}

/** The character's line: their name, what happens to them, and the start of their description. */
export function characterLines(found: CharacterFile, character: NonNullable<CharacterFile['character']>) {
  const name = character.name || 'The character'
  const hint = found.already ? `${found.already.name} is already one of your companions, so they start unticked.` : 'Moves into town with a job, a home and a routine of their own.'
  const about = character.about.length >= 300 ? `${character.about.trimEnd()}…` : character.about
  return { name, hint, about }
}

export function pictureHint(picture: NonNullable<CharacterFile['picture']>): string {
  if (!picture.usable) return picture.note ?? "It can't be used."
  return picture.portrait ? 'Becomes their profile picture.' : 'Goes with their reference pictures.'
}
