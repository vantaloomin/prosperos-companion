import type { PairStage, PairTie } from '../../types'

/** The stages a companion and someone else can be at, the same five as closeness with the user. */
export const PAIR_STAGES = ['Just met', 'Getting to know each other', 'Comfortable', 'Close', 'Deeply close']

/** "Close", or "Close · Maya feels Comfortable" when the two feel differently. */
export function stageText(stage: PairStage, other: string): string {
  return stage.level === stage.their_level ? stage.name : `${stage.name} · ${other} feels ${stage.their_name}`
}

/** "Sally and Billy: Comfortable", or both directions when they differ. */
export function tieText(name: string, tie: PairTie): string {
  const first = name.split(' ')[0]
  const other = tie.name.split(' ')[0]
  if (tie.feels.level === tie.they_feel.level) return `${first} and ${other}: ${tie.feels.name}`
  return `${first} feels ${tie.feels.name} with ${other}; ${other} feels ${tie.they_feel.name}`
}

/** What their stage comes from, so it reads as history rather than a setting. */
export function tieWhy(tie: PairTie): string {
  const parts = []
  if (tie.group_days) parts.push(`talked in a group on ${tie.group_days} ${tie.group_days === 1 ? 'day' : 'days'}`)
  if (tie.meetings) parts.push(`ran into each other ${tie.meetings === 1 ? 'once' : `${tie.meetings} times`}`)
  return parts.length ? parts.join(', ') : ''
}
