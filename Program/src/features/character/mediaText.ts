/** Wording for the Reading, watching, listening panel (companion/life/media.py). */
import type { MediaNow, MediaView } from '../../types'

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

/** Who made it, for the change form's second field. */
export function byLabel(kind: MediaNow['kind']): string {
  return { book: 'Author', show: 'Where it is on (optional)', music: 'Artist' }[kind]
}

/** Hidden values: "About 45% through, 9 days to go, will finish." */
export function itemNumbers(view: MediaView, id: string): string | null {
  const found = view.numbers?.items[id]
  if (!found) return null
  return `${found.along}% through, ${found.days_left} ${found.days_left === 1 ? 'day' : 'days'} to go, will ${found.ends === 'finish' ? 'finish it' : 'put it down'}.`
}

/** Hidden values: how keen they are and the slider's odds. */
export function numbersLine(view: MediaView): string | null {
  const numbers = view.numbers
  if (!numbers) return null
  const keen = ['not much', 'a little', 'a fair bit', 'a lot']
  return `Reads ${keen[numbers.reader]}, watches ${keen[numbers.watcher]}${numbers.library ? ', borrows books from the library' : ''}. ` +
    `Gives up on what they don't like ${numbers.drop}% of the time; passes on what they love ${numbers.recommend}% of the time.`
}
