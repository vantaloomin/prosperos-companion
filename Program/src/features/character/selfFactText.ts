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
