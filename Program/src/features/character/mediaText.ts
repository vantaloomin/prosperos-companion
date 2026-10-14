/** Wording for the Reading, watching, listening panel (companion/life/media.py). */
import type { MediaNow, MediaView } from '../../types'
import { panelTitle } from './panelText.ts'

export const MEDIA_KEY = ['media']

/** The Realism slider's steps (Settings > Realism > Their days). */
export const MEDIA_LEVELS = [
  { value: 0, label: 'Off', hint: 'Nobody keeps track of what they read, watch or listen to.' },
  { value: 1, label: 'Light', hint: 'Always a book, a show and a song on the go. They finish what they start and mostly like it.' },
  { value: 2, label: 'True to life', hint: 'Mixed feelings about what they finish, and now and then something they give up on partway.' },
  { value: 3, label: 'Dramatic', hint: 'Strong opinions, shows binged in a weekend, more given up on, and more of what they love passed on to you.' },
] as const

/** The row's label: "Reading", "Watching" or "On repeat" (in the past, "Following" and "Humming" read the same way). */
export function kindLabel(kind: MediaNow['kind']): string {
  return { book: 'Reading', show: 'Watching', music: 'On repeat' }[kind]
}

/** The noun for the change form: "book", "show" or "song". */
export function kindNoun(kind: MediaNow['kind']): string {
  return { book: 'book', show: 'show', music: 'song' }[kind]
}

/** The change form's second field: the author or artist (a show has none). */
export function byLabel(kind: MediaNow['kind']): string | null {
  return { book: 'Author', show: null, music: 'Artist' }[kind]
}

/** Muted examples in the change form's empty boxes. */
export function examples(kind: MediaNow['kind']): { title: string; by: string } {
  return { book: { title: 'e.g. Piranesi', by: 'e.g. Susanna Clarke' }, show: { title: 'e.g. Slow Horses', by: '' },
    music: { title: 'e.g. Espresso', by: 'e.g. Sabrina Carpenter' } }[kind]
}

/** "Dana's books, shows and music", by first name like the other Character panels. */
export function panelHeading(name: string): string {
  return panelTitle(name, 'books, shows and music')
}

/** The text before and after the title, to set the title off; null when the title is not in it. */
export function titled(text: string, title: string): [string, string] | null {
  const at = title ? text.indexOf(title) : -1
  return at < 0 ? null : [text.slice(0, at), text.slice(at + title.length)]
}

/** "Finished X by Y: loved it." as ["Finished X by Y", "loved it"]; a line with no verdict stays whole. */
export function verdictSplit(text: string): [string, string | null] {
  const at = text.lastIndexOf(': ')
  if (at < 0) return [text, null]
  return [text.slice(0, at), text.slice(at + 2).replace(/\.$/, '')]
}

/** How many Lately rows show before "Show N more". */
export const LATELY_SHOWN = 5

/** Hidden values: "About 45% through, 9 days to go, will finish." */
export function itemNumbers(view: MediaView, id: string, kind?: MediaNow['kind']): string | null {
  const found = view.numbers?.items[id]
  if (!found) return null
  const days = `${found.days_left} more ${found.days_left === 1 ? 'day' : 'days'}`
  if (kind === 'music') return `On repeat for ${days}.`
  return `${found.along}% through, ${found.days_left} ${found.days_left === 1 ? 'day' : 'days'} to go, will ${found.ends === 'finish' ? 'finish it' : 'put it down'}.`
}

/** Hidden values: how keen they are and the slider's odds. */
export function numbersLine(view: MediaView): string | null {
  const numbers = view.numbers
  if (!numbers) return null
  const keen = ['not much', 'a little', 'a fair bit', 'a lot']
  return `Reads ${keen[numbers.reader]}, watches ${keen[numbers.watcher]}${numbers.library ? ', borrows books from the library' : ''}. ` +
    `Gives up on what they don't like ${numbers.drop}% of the time; tells you about something they loved ${numbers.recommend}% of the time.`
}
