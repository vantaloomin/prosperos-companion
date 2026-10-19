import type { KindChoices, KindShown } from '../../types'

/** "600 years", "1,000 years". */
export function yearsText(years: number) {
  return `${years.toLocaleString('en-US')} years`
}

/** The Kind picker's first option, the app's pick: "As their words say (Elf)", or "Human" when there is nothing to read. */
export function foundOption(foundLabel: string, fromWords: boolean) {
  return fromWords ? `As their description says (${foundLabel})` : `As the app picks (${foundLabel})`
}

/** How long they live's first option: "As their kind (about 600 years)", "As their kind (doesn't age)". */
export function asKindOption(kindYears: number | null) {
  return kindYears === null ? "As their kind (doesn't age)" : `As their kind (about ${yearsText(kindYears)})`
}

/** "About 48 in human terms": under the pickers, only when it differs from the age they are. */
export function humanTermsText(shown: KindShown | undefined, age: number | null | undefined) {
  if (!shown || shown.life_age === null || shown.life_age === undefined || shown.life_age === age) return ''
  return `About ${shown.life_age} in human terms.`
}

/** The lifespans offered, with the one already picked kept when it is not on the list (a city's own). */
export function spanChoices(choices: KindChoices | undefined, own: number | null) {
  const spans = choices?.spans ?? [80, 150, 300, 600, 1000]
  return own && !spans.includes(own) ? [...spans, own].sort((a, b) => a - b) : spans
}

/** The summary of a folded kind section on someone's card: "Kind: Elf, about 600 years". */
export function kindSummary(shown: KindShown) {
  if (shown.years === null) return shown.kind === 'ageless' ? `Kind: ${shown.label}` : `Kind: ${shown.label}, doesn't age`
  return `Kind: ${shown.label}, about ${yearsText(shown.years)}`
}
