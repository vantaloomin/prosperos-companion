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

/** Why the stage is what it is: a hold wins, then a ceiling and gentle cooling, then history from where it started or was set. */
export function stageText(state: Closeness, name: string): string {
  if (state.held_level) {
    const grown = state.stages[state.grown_level - 1]
    return state.held_level === state.grown_level
      ? `You are keeping ${name} at ${state.name}. Without that it would be here too.`
      : `You are keeping ${name} at ${state.name}. Without that it would be ${grown}.`
  }
  if (state.cooled_steps) return cooledText(state)
  const capped = state.ceiling_level && state.ceiling_level < state.earned_level
  if (capped) return `${state.name}, the closest you let it get. From your shared history alone it would be ${state.stages[state.earned_level - 1]}.`
  if (state.set_on) return `${state.name}. You set it on ${dayText(state.set_on)} and it grows from there.`
  if (state.starting_level > 1) return `${state.name}. You started at ${state.stages[state.starting_level - 1]} and it grows from there.`
  return `${state.name}, from your shared history.`
}

/** Gentle cooling the user turned on: how far it cooled from, and how soon talking brings it back. */
function cooledText(state: Closeness): string {
  const from = state.stages[Math.min(state.earned_level, state.ceiling_level ?? state.earned_level) - 1]
  const back = state.warm_days_left ? ` Talking on ${plural(state.warm_days_left, 'more day', 'more days')} brings a step back.` : ''
  return `${state.name}: it has cooled ${state.cooled_steps === 1 ? 'a step' : 'two steps'} from ${from} after a long time apart.${back}`
}

export function milestoneText(milestone: ClosenessMilestone, stages: string[]): string {
  const stage = stages[milestone.level - 1]
  if (milestone.kind === 'start') return `Started at ${stage}.`
  if (milestone.kind === 'set') return `You set it to ${stage} on ${dayText(milestone.on ?? '')}.`
  return `${stage} on ${dayText(milestone.on ?? '')}, after ${plural(milestone.days ?? 0, 'day', 'days')} talking and ${plural(milestone.moments ?? 0, 'shared moment', 'shared moments')}.`
}

export const OPENNESS = [
  'A little guarded. Keeps it light, gives small answers to personal questions, and uses no nicknames.',
  'Shares opinions, small frustrations and the stories you tell someone new; keeps heavier things for later.',
  'Shares personal stories and everyday worries, teases lightly, and may come up with a nickname. Deepest fears take time.',
  'Open about fears and what matters, brings up shared moments and running jokes, and sometimes says what is on their mind.',
  'Long familiarity: shorthand, in-jokes, honesty about hard things, and offers their feelings without being asked.',
]
