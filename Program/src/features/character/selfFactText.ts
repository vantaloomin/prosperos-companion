import type { SelfFact } from '../../types'

/** One line for a fact the companion stated about themselves, as Character Studio lists it. */
export function selfFactText(fact: SelfFact): string {
  if (fact.category === 'person' || fact.category === 'pet') return `Their ${fact.subject} is named ${fact.value}`
  if (fact.category === 'favorite') return `Favorite ${fact.subject}: ${fact.value}`
  if (fact.category === 'never') return `Has never ${fact.subject}`
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
