import type { View } from '../../companion.ts'
import type { WatchFocus, WatchLine } from '../../types.ts'

/** Inner voice (Settings > Realism > Their days, companion/life/narrator.py): how much of their mind the Watching page tells. */
export const INNER_VOICE_LEVELS = [
  { label: 'Just what happened', hint: 'Only what they did and what happened to them, no thoughts.' },
  { label: 'A few thoughts', hint: "What happened, and the one thing on their mind each evening." },
  { label: 'True to life', hint: 'What happened, how they feel, and a thought after what stood out.' },
  { label: 'Everything on their mind', hint: 'A thought after everything, and the passing ones in between.' },
] as const

/** A person's first name, as the narrator calls them. */
export function firstName(name: string): string {
  return name.trim().split(/\s+/)[0] || name
}

/** The picker's groups, in order: companions, each companion's people in town, townsfolk the main companion has met,
 * then the ones the app picked for a busy week. The group says where each person comes from. */
export function focusGroups(choices: WatchFocus[]): { label: string; people: WatchFocus[] }[] {
  const groups = [{ label: 'Companions', people: choices.filter((choice) => choice.kind === 'companion') }]
  const owners = [...new Set(choices.filter((choice) => choice.kind === 'circle').map((choice) => choice.owner ?? ''))]
  for (const owner of owners) {
    groups.push({ label: owner ? `${owner}'s people` : 'Their people', people: choices.filter((choice) => choice.kind === 'circle' && (choice.owner ?? '') === owner) })
  }
  const town = choices.filter((choice) => choice.kind === 'townsperson')
  const met = town.filter((choice) => choice.source === 'met')
  groups.push(
    { label: met[0]?.owner ? `${met[0].owner} has met` : 'Met around town', people: met },
    { label: 'Busy around town this week', people: town.filter((choice) => choice.source === 'busy') },
    { label: 'Around town', people: town.filter((choice) => !choice.source) },
  )
  return groups.filter((group) => group.people.length > 0)
}

/** Talking to a companion steps back in (a townsperson's own world is BecomeThem). */
export function stepInLabel(focus: WatchFocus): string {
  return `Talk to ${firstName(focus.name)}`
}

/** The button that starts a separate world as a townsperson: an offer to try, not a switch. */
export function becomeLabel(name: string): string {
  return `Try life as ${firstName(name)}`
}

/** A line's time where they live ("9:30 AM"); how they feel now reads "Now". */
export function lineTime(line: WatchLine, timezone: string): string {
  if (line.kind === 'mood') return 'Now'
  try {
    return new Date(line.at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', timeZone: timezone })
  } catch {
    return new Date(line.at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
  }
}

/** What kind of line it is, for screen readers and the small label beside a dream or a thought. */
export const LINE_LABELS: Partial<Record<WatchLine['kind'], string>> = {
  dream: 'Dream', thought: 'On their mind', news: 'Heard', story: 'Unfolding', chapter: 'New chapter', mood: 'Feeling',
  moment: 'A small moment', met: 'Crossed paths', family: 'Family', love: 'Love life',
}

/** Where the "Just watching" banner shows: a chat with a companion or a group, where writing would step them back in. */
export function inChat(view: View): boolean {
  return view === 'conversation' || view.startsWith('group/')
}
