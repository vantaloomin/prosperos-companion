/** Words that fit what is typed: ones starting with it first, then ones containing it. A box that already holds
 * one of the words shows them all, so another can be picked without clearing it first. */
export function suggestionsFor(options: string[], typed: string): string[] {
  const query = typed.trim().toLowerCase()
  if (!query || options.some((option) => option.toLowerCase() === query)) return options
  const starts = options.filter((option) => option.toLowerCase().startsWith(query))
  return [...starts, ...options.filter((option) => !starts.includes(option) && option.toLowerCase().includes(query))]
}
