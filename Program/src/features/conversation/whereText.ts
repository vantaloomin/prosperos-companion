/** Together or apart (companion/life/together.py): the "where you are" strip's state and wording, kept apart from the component for tests. */
import { timeText, type Outing } from '../today/outingText.ts'

export const WHERE_KEY = ['where']

/** Out somewhere, at their place, at yours, or a knock at your door; apart in the same city, or long distance. On a call comes next. */
export type WhereKind = 'apart' | 'long-distance' | 'out' | 'theirs' | 'yours' | 'knock'
export interface WhereOuting extends Outing { not_now: boolean }
export interface WhereState { state: 'together' | 'apart'; kind: WhereKind; text: string; outing: WhereOuting | null }
export interface CompanionWhere { state: 'together' | 'apart'; kind: WhereKind; text: string }

/** What the strip says: a lead, the place (linked to the map when it is out in town) and how long. */
export interface StripLine { lead: string; place: { id: string; name: string } | null; tail: string }
/** The strip's one button: Head home, Say goodbye, Not now, or Undo just after one of those. */
export interface StripAction { action: 'home' | 'undo'; label: string }

/** Null while apart: the strip shows only time together (and, later, a call). */
export function stripLine(where: WhereState | undefined, name: string): StripLine | null {
  const outing = where?.outing
  if (!where || !outing) return null
  return outing.state === 'done' ? endedLine(where.kind, outing, name) : liveLine(where.kind, outing, name)
}

function endedLine(kind: WhereKind, outing: WhereOuting, name: string): StripLine {
  if (kind === 'yours' || kind === 'knock') return { lead: `${name} headed home.`, place: null, tail: '' }
  return { lead: `Headed home from ${kind === 'theirs' ? `${name}'s place` : outing.place.name}.`, place: null, tail: '' }
}

function liveLine(kind: WhereKind, outing: WhereOuting, name: string): StripLine {
  const tail = ` until ${timeText(outing.until_time)}`
  if (kind === 'out') return { lead: 'Together at ', place: { id: outing.place.id, name: outing.place.name }, tail }
  if (kind === 'theirs') return { lead: `At ${name}'s place`, place: null, tail }
  if (kind === 'knock' && outing.not_now) return { lead: `${name} dropped by and is at your place`, place: null, tail }
  return { lead: `${name} is at your place`, place: null, tail }
}

export function stripAction(where: WhereState | undefined): StripAction | null {
  const outing = where?.outing
  if (!where || !outing) return null
  if (outing.state === 'done') return outing.undo ? { action: 'undo', label: 'Undo' } : null
  if (where.kind === 'knock' && outing.not_now) return { action: 'home', label: 'Not now' }
  if (where.kind === 'yours' || where.kind === 'knock') return { action: 'home', label: 'Say goodbye' }
  return { action: 'home', label: 'Head home' }
}

/** Whether the chat writes in person now: texting habits like bursts stop while they are together. */
export function inPerson(where: WhereState | undefined): boolean {
  return where?.state === 'together'
}

/** The Getting together slider's steps (Settings > Realism, companion/life/together.py). */
export const TOGETHER_LEVELS = [
  { label: 'Only when you ask', hint: 'They never suggest meeting up or ask you over on their own. Ask them and they still come when they can.' },
  { label: 'Now and then', hint: 'Once in a while they suggest meeting up or ask you over. Nobody turns up at your door unannounced.' },
  { label: 'True to life', hint: 'They suggest meeting up and ask you over about as often as real friends do, and someone close who lives nearby sometimes knocks unannounced. Never in your quiet hours.' },
  { label: 'Often', hint: 'They want to see you a lot: plans most weeks, invitations over, and close companions in your city dropping by more often. Never in your quiet hours.' },
]
