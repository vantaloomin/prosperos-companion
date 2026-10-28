/** Words that fit what is typed: ones starting with it first, then ones containing it. A box that already holds
 * one of the words shows them all, so another can be picked without clearing it first. */
export function suggestionsFor(options: string[], typed: string): string[] {
  const query = plain(typed)
  if (!query || options.some((option) => plain(option) === query)) return options
  const starts = options.filter((option) => plain(option).startsWith(query))
  return [...starts, ...options.filter((option) => !starts.includes(option) && plain(option).includes(query))]
}

/** Time zone names keep underscores (America/New_York); the list shows them as spaces and "new york" finds them. */
export const shownAs = (option: string) => option.replaceAll('_', ' ')

const plain = (text: string) => shownAs(text).trim().toLowerCase()
