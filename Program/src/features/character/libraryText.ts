/** Words for the reference library (companion/library.py, companion/library_online.py). */

export interface LibraryBook {
  id: string; name: string; world: boolean; source_format: string; source_file: string; online: string
  city_id: string | null; enabled: boolean; passages: number; created_at: string; updated_at: string
}
export interface Passage { id: string; title: string; text: string }
/** A book the app can download from its author's site (the Neokosmos wiki, offered on Grandport's card). */
export interface OnlineBook {
  key: string; name: string; city_id: string; city_name: string; url: string; author: string; licence: string; licence_url: string
  book_id: string | null; updated_at: string | null
}

export const LIBRARY_KEY = ['library']
export const ONLINE_KEY = ['library-online']
export const LIBRARY_TYPES = '.txt,.md,.markdown,.html,.htm,.epub'
/** Above this the server turns a file down (companion/models.py LibraryFile). */
export const LIBRARY_MAX_BYTES = 10 * 1024 * 1024

const count = (value: number, word: string) => `${value.toLocaleString('en-US')} ${word}${value === 1 ? '' : 's'}`

/** Whose library a page shows: a companion's ("Mira's library") or the world's. */
export function shelfName(world: boolean, name?: string): string {
  return world ? "the world's library" : `${name ?? 'their'}'s library`
}

export function libraryIntro(world: boolean, name?: string): string {
  const who = world ? 'every companion in this world' : name ?? 'they'
  return `Long texts ${who} can draw on: a novel, a script, transcripts or a wiki export. Only the few passages that fit what you are talking about join each reply.`
}

/** Under a book's name: whose it is, how big, and what it came from. */
export function librarySummary(book: LibraryBook, cityName?: string): string {
  const whose = book.city_id ? `Everyone in ${cityName ?? 'its city'}` : book.world ? 'Everyone in this world' : 'This companion'
  return `${whose} · ${count(book.passages, 'passage')} · ${book.source_format}`
}

/** What adding a book did, in one sentence. `shelf` is whose library: "Mira's library" or "the world's library". */
export function addedText(added: { name: string; passages: number }, shelf: string): string {
  return `${added.name} is in ${shelf}: ${count(added.passages, 'passage')}. The few that fit what you talk about join each reply.`
}

/** Under a book's passages: how many are shown, and how to find the rest. */
export function shownText(shown: number, total: number, searching: boolean): string {
  if (searching) return shown === 0 ? 'No passages match.' : shown === 1 ? 'The one passage that matches.' : `The ${shown} passages that match best.`
  return shown < total ? `The first ${shown} of ${count(total, 'passage')}. Search to find others.` : `All ${count(total, 'passage')}.`
}

/** What downloading an online book did. */
export function downloadedText(added: { name: string; passages: number; replaced: boolean }, author: string, cityName: string): string {
  const what = added.replaced ? `${added.name} is up to date` : `${added.name} is in this world's library`
  return `${what}: ${count(added.passages, 'passage')} from ${author}'s site. Companions in ${cityName} draw on it.`
}

/** The credit an online book carries on its page. */
export function creditText(online: OnlineBook): string {
  return `By ${online.author}, shared under ${online.licence}. Downloaded from ${online.url.replace(/^https?:\/\//, '').replace(/\/$/, '')}.`
}
