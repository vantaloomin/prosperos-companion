/** Wording for the Pastimes panel (companion/life/hobbies.py). */
import type { Hobby } from '../../types'

export const HOBBIES_KEY = ['hobbies']

/** Settings > Realism: how much their pastimes move on their own. */
export const HOBBY_LEVELS = [
  { value: 0, label: 'Off', hint: 'Their pastimes stay as they are: no new ones, none dropped, no milestones.' },
  { value: 1, label: 'Light', hint: 'They keep at their pastimes and get better. Now and then one slows down for a while, but they never give one up.' },
  { value: 2, label: 'True to life', hint: 'They get better with practice and hit milestones. Some weeks one stalls; one the app picked can be given up after a long dry spell, and now and then they try something new.' },
  { value: 3, label: 'Dramatic', hint: 'More stalls and comebacks, more new things tried, and the ones the app picked get given up more often.' },
] as const

const SOURCES: Record<Hobby['source'], string> = { interest: 'From their interests', user: 'You added this', app: 'Picked up on their own' }

/** Where a pastime came from, in words; the ones from their interests and the user's never get given up. */
export function sourceText(hobby: Hobby): string {
  if (hobby.source === 'app' && hobby.kept) return 'Picked up on their own, kept'
  return SOURCES[hobby.source]
}

/** The meta line under the title: the level in words, then how long and how often, e.g. "Good at it now",
 * "about eight years in", "twice a week". A stalled pastime leaves out how often (its callout says why);
 * a given-up one is only its status. */
export function metaParts(hobby: Hobby, levelNames: string[]): { level: string; rest: string[] } {
  if (hobby.status === 'dropped') return { level: '', rest: [hobby.status_text.replace(/\.$/, '')] }
  const level = levelLabel(levelNames[hobby.level] ?? '')
  const since = hobby.since_text.charAt(0).toLowerCase() + hobby.since_text.slice(1)
  const often = hobby.status_text.replace(/\.$/, '')
  return { level, rest: hobby.status === 'stalled' ? [since] : [since, often.charAt(0).toLowerCase() + often.slice(1)] }
}

/** "Kim gave up rock climbing." for the inline undo row. */
export function gaveUpLine(hobby: Hobby, name: string): string {
  return `${name} gave up ${hobby.name}.`
}

/** "Kim learned their first barre chord." from a log line about them. */
export function recentLine(text: string, name: string): string {
  const trimmed = text.trim()
  if (!trimmed) return ''
  return `${name} ${trimmed}${/[.!?]$/.test(trimmed) ? '' : '.'}`
}

/** Hidden values: "Skill 34 of 100 (best 36), 41 sessions, next milestone at 38, talent 1.1." */
export function hobbyNumbers(hobby: Hobby): string | null {
  const found = hobby.numbers
  if (!found) return null
  return `Skill ${found.skill} of 100 (best ${found.best}), ${found.sessions} ${found.sessions === 1 ? 'session' : 'sessions'}, next milestone at ${found.next_at}, talent ${found.talent.toFixed(2)}.`
}

/** Short dates for the Lately list: "Oct 5". */
export function hobbyDate(value: string): string {
  return new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

/** A capital for the level menu: "Just starting out". */
export function levelLabel(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1)
}
