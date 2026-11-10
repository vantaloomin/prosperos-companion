/** Their own words in Settings > Memory (OwnWords.tsx): the data and the few words each row shows. */

export type Action = 'drop' | 'swap' | 'keep' | 'dismiss'
export interface WordRule { id: string; phrase: string; action: Action; replacement: string; everyone: boolean }
export interface Caught { phrase: string; kind: 'stock' | 'repeat'; step: number }
export interface OwnWordsData { rules: WordRule[]; caught: Caught[]; limit: number }

export const OWN_WORDS_KEY = ['own-words']

/** What happens to a caught phrase now, in a few words. */
export function caughtNote(item: Caught): string {
  if (item.step >= 3) return 'Now left out'
  if (item.step === 2) return 'Same question again'
  return item.kind === 'stock' ? 'Stock wording' : 'Repeated'
}

/** What a rule on the list does, in a few words. */
export function ruleNote(rule: WordRule): string {
  const where = rule.everyone ? 'every world' : 'this world'
  return `${ruleAction(rule)} · ${where}`
}

function ruleAction(rule: WordRule): string {
  if (rule.action === 'keep') return 'Kept as theirs'
  if (rule.action === 'swap') return rule.replacement.trim() ? `Swapped for “${rule.replacement}”` : 'Swapped for nothing'
  return 'Dropped'
}

/** A caught phrase as it reads in a reply: the bank and the habit finder keep words lower case, but "I" is a capital. */
export function shownPhrase(phrase: string): string {
  return phrase.replace(/(^|[^\p{L}'’])i(?=$|[^\p{L}]|['’](?:m|d|ll|ve)\b)/gu, '$1I')
}

/** "Caught lately in Dana's replies": their first name, or a plain title before a companion exists. */
export function caughtTitle(name: string): string {
  const first = name.trim().split(/\s+/)[0]
  return first ? `Caught lately in ${first}’s replies` : 'Caught lately'
}
