import type { Closeness, ClosenessMilestone } from '../../types'

export const CLOSENESS_KEY = ['closeness']

const plural = (count: number, one: string, many: string) => `${count} ${count === 1 ? one : many}`

/** A calendar day (YYYY-MM-DD) as words, without shifting it through a timezone. */
export function dayText(day: string): string {
  const [year, month, date] = day.split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, date)).toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' })
}

/** What the current stage is built from, in words. */
export function basisText(state: Closeness): string {
  if (state.days_talked === 0) return state.counted_from ? 'Counting restarted when you reset it. Nothing is counted yet.' : 'You have not talked yet.'
  const since = state.counted_from ? ' since you reset it' : ''
  const moments = state.shared_moments === 0 ? 'no shared moments in Memories'
    : state.counted_moments < state.shared_moments
      ? `${plural(state.shared_moments, 'shared moment', 'shared moments')} in Memories (${state.counted_moments} counted, never more than the days you talked)`
      : plural(state.shared_moments, 'shared moment', 'shared moments') + ' in Memories'
  return `You have talked on ${plural(state.days_talked, 'day', 'days')}${since}, with ${moments}.`
}

/** Why the stage is what it is: a hold the user set wins over shared history. */
export function stageText(state: Closeness, name: string): string {
  if (state.held_level) {
    const grown = state.stages[state.grown_level - 1]
    return state.held_level === state.grown_level
      ? `You are holding ${name} at ${state.name}. Shared history alone puts you here too.`
      : `You are holding ${name} at ${state.name}. From shared history alone it would be ${grown}.`
  }
  return `${state.name}, from your shared history.`
}

export function milestoneText(milestone: ClosenessMilestone, stages: string[]): string {
  return `${stages[milestone.level - 1]} on ${dayText(milestone.on)}, after ${plural(milestone.days, 'day', 'days')} talking and ${plural(milestone.moments, 'shared moment', 'shared moments')}.`
}

export const OPENNESS = [
  'Friendly but a little reserved. Shares everyday things, not private worries, and uses no nicknames.',
  'Shares opinions, small frustrations and the stories you tell someone new.',
  'Shares personal stories, hopes and worries, teases lightly, and may come up with a nickname.',
  'Open about fears and what matters, and brings up shared moments and running jokes.',
  'Talks with long familiarity: shorthand, in-jokes and honesty about hard things.',
]
