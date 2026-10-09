import type { SelfFact } from '../../types'

/** One line for a fact the companion stated about themselves, as Character Studio lists it. */
export function selfFactText(fact: SelfFact): string {
  if (fact.category === 'person' || fact.category === 'pet') return `Their ${fact.subject} is named ${fact.value}`
  if (fact.category === 'favorite') return `Favorite ${fact.subject}: ${fact.value}`
  if (fact.category === 'never') return `Has never ${fact.subject}`
  if (fact.category === 'said') return `Said: “${fact.value}”`
  if (fact.category === 'detail') return `${fact.subject.charAt(0).toUpperCase()}${fact.subject.slice(1)}: ${fact.value}`
  return `${fact.label}: ${fact.value}`
}

/** Conflicts first, so a contradiction waiting for a decision is seen. */
export function orderFacts(facts: SelfFact[]): SelfFact[] {
  return [...facts.filter((fact) => fact.status === 'conflict'), ...facts.filter((fact) => fact.status !== 'conflict')]
}

/** Why a conflicting fact waits: the user said it was wrong, the definition or circle says otherwise, or the
 * companion said something different before. */
export function conflictText(fact: SelfFact): string {
  if (fact.user_said !== undefined) return fact.user_said ? `you said: “${fact.user_said}”` : 'you said this was wrong'
  if (fact.definition_says) return `their character says ${fact.definition_says}`
  if (fact.circle_person) return `their circle has ${fact.circle_person}`
  return 'contradicts something they said earlier'
}

/** Remember this on a companion message: what they said about themselves, kept for later replies. */
export function keptSaying(name: string, facts: SelfFact[]): string {
  const where = `You can remove ${facts.length === 1 ? 'it' : 'them'} on ${name}'s Character page.`
  // A line no rule could read is kept whole; quoting it back would only repeat the message.
  if (facts.every((fact) => fact.category === 'said')) return `${name} will stay consistent with what they said there. ${where}`
  return `${name} will stay consistent with ${facts.length === 1 ? 'this' : 'these'}: ${facts.map(selfFactText).join('; ')}. ${where}`
}
