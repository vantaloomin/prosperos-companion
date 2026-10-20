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

/** The picker's groups, in order: companions, then townsfolk. */
export function focusGroups(choices: WatchFocus[]): { label: string; people: WatchFocus[] }[] {
  const groups = [
    { label: 'Companions', people: choices.filter((choice) => choice.kind === 'companion') },
    { label: 'Around town', people: choices.filter((choice) => choice.kind === 'townsperson') },
  ]
  return groups.filter((group) => group.people.length > 0)
}

/** What "Step in" does for this person: talk to a companion, or become a townsperson. */
export function stepInLabel(focus: WatchFocus): string {
  return focus.kind === 'companion' ? `Talk to ${firstName(focus.name)}` : `Become ${firstName(focus.name)}`
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
  moment: 'A small moment', met: 'Crossed paths',
}

/** Where the "Just watching" banner shows: a chat with a companion or a group, where writing would step them back in. */
export function inChat(view: View): boolean {
  return view === 'conversation' || view.startsWith('group/')
}
