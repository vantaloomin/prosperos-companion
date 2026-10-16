/** Together or apart (companion/life/together.py): the "where you are" strip's state and wording, kept apart from the component for tests. */
import { dayText, timeText, type Outing } from '../today/outingText.ts'

export const WHERE_KEY = ['where']

/** Out somewhere, at their place, at yours, or a knock at your door; apart in the same city, or long distance; on a call, or ringing you; a weekend visit across the distance, them staying with you or you with them. */
export type WhereKind = 'apart' | 'long-distance' | 'out' | 'theirs' | 'yours' | 'knock' | 'call' | 'ringing' | 'staying' | 'hosting' | 'home'
export interface WhereOuting extends Outing { not_now: boolean }
/** A call (companion/life/calls.py): on, ringing, or one that just ended or went unanswered. `direction` is who called: 'you' or 'them'. */
export interface WhereCall { id: string; direction: 'you' | 'them'; status: 'ringing' | 'on' | 'missed' | 'declined' | 'ended'; started_at: string | null; until_at: string | null; ended_at: string | null }
/** A weekend visit under way (companion/life/long_distance.py): 'to-you' when they came to stay with you, 'host' when you went to stay with them. `leave_at` is when the visit ends on its last day. */
export interface WhereVisit { id: string; direction: 'to-you' | 'host'; city_name: string; start_date: string; end_date: string; leave_at: string }
/** Living together (companion/life/moving_in.py): both home of an evening, or you out for a while (`until`). */
export interface WhereHome { status: 'home' | 'out'; until?: string }
export interface WhereState { state: 'together' | 'apart' | 'call'; kind: WhereKind; text: string; outing: WhereOuting | null; call?: WhereCall | null; visit?: WhereVisit | null; home?: WhereHome | null }
export interface CompanionWhere { state: 'together' | 'apart' | 'call'; kind: WhereKind; text: string }

/** What the strip says: a lead, the place (linked to the map when it is out in town) and how long. */
export interface StripLine { lead: string; place: { id: string; name: string } | null; tail: string }
/** The strip's one button: Head home, Say goodbye, Not now, or Undo just after one of those. */
export interface StripAction { action: 'home' | 'undo'; label: string }
/** A call's buttons: Decline and Answer while it rings, End call while it is on, Call back after one you missed. */
export interface CallAction { action: 'answer' | 'decline' | 'end' | 'call'; label: string }

/** Null while apart: the strip shows only time together, or a call. */
export function stripLine(where: WhereState | undefined, name: string): StripLine | null {
  if (where?.call) return callLine(where.call, name)
  if (where?.visit) return visitLine(where.visit, name)
  const outing = where?.outing
  if (!where || !outing) return null
  return outing.state === 'done' ? endedLine(where.kind, outing, name) : liveLine(where.kind, outing, name)
}

function endedLine(kind: WhereKind, outing: WhereOuting, name: string): StripLine {
  if (kind === 'yours' || kind === 'knock') return { lead: `${name} headed home.`, place: null, tail: '' }
  return { lead: sentence(`Headed home from ${kind === 'theirs' ? `${name}'s place` : outing.place.name}`), place: null, tail: '' }
}

/** A full stop, unless the words already end in one ("Power Plant Live!", "Pastries & Co."). */
function sentence(words: string): string {
  return /[.!?]$/.test(words) ? words : `${words}.`
}

function liveLine(kind: WhereKind, outing: WhereOuting, name: string): StripLine {
  const tail = ` until ${timeText(outing.until_time)}`
  if (kind === 'out') return { lead: 'Together at ', place: { id: outing.place.id, name: outing.place.name }, tail }
  if (kind === 'theirs') return { lead: `At ${name}'s place`, place: null, tail }
  if (kind === 'knock' && outing.not_now) return { lead: `${name} dropped by and is at your place`, place: null, tail }
  return { lead: `${name} is at your place`, place: null, tail }
}

/** A weekend visit: who is staying with whom, and until when ("until Sun, Oct 18"). */
export function visitLine(visit: WhereVisit, name: string): StripLine {
  const tail = ` until ${dayText(visit.end_date)}`
  if (visit.direction === 'to-you') return { lead: `${name} is staying with you`, place: null, tail }
  return { lead: `Staying with ${name} in ${visit.city_name}`, place: null, tail }
}

/** Living together: home together of an evening, with Heading out; or you out for a while, with I'm home. Only
 * when nothing else (a call, a visit, an outing) is on the strip. */
export function homeLine(where: WhereState | undefined, name: string): { lead: string; action: 'out' | 'home'; label: string } | null {
  if (!where?.home || where.call || where.visit || where.outing) return null
  if (where.home.status === 'out') return { lead: `You're out. Texting with ${name}`, action: 'home', label: "I'm home" }
  return { lead: `Home together with ${name}`, action: 'out', label: 'Heading out' }
}

/** What the strip says about a call; how long it has been on is ticked by the strip itself (callClock). */
export function callLine(call: WhereCall, name: string): StripLine {
  const line = (lead: string, tail = '') => ({ lead, place: null, tail })
  if (call.status === 'on') return line(`On a call with ${name}`)
  if (call.status === 'ringing') return line(`${name} is calling`)
  if (call.status === 'ended') return line('Call ended', call.started_at && call.ended_at ? ` after ${minutesText(Date.parse(call.ended_at) - Date.parse(call.started_at))}.` : '.')
  if (call.status === 'declined') return line(`You declined ${name}'s call.`)
  return line(call.direction === 'you' ? `${name} didn't pick up.` : `Missed call from ${name}.`)
}

export function callActions(call: WhereCall | null | undefined): CallAction[] {
  if (!call) return []
  // Answer last, nearest the thumb, as phones do.
  if (call.status === 'ringing') return [{ action: 'decline', label: 'Decline' }, { action: 'answer', label: 'Answer' }]
  if (call.status === 'on') return [{ action: 'end', label: 'End call' }]
  if (call.status === 'missed' && call.direction === 'them') return [{ action: 'call', label: 'Call back' }]
  return []
}

/** "12 minutes", "1 minute", "less than a minute": how long a call that ended lasted. */
export function minutesText(ms: number): string {
  const minutes = Math.round(ms / 60_000)
  return minutes < 1 ? 'less than a minute' : `${minutes} minute${minutes === 1 ? '' : 's'}`
}

/** "4:05", "1:02:09": how long a call has been on. */
export function callClock(ms: number): string {
  const seconds = Math.max(0, Math.floor(ms / 1000))
  const [hours, minutes, rest] = [Math.floor(seconds / 3600), Math.floor(seconds / 60) % 60, seconds % 60]
  const two = (value: number) => String(value).padStart(2, '0')
  return hours ? `${hours}:${two(minutes)}:${two(rest)}` : `${minutes}:${two(rest)}`
}

/** Whether the header's Call button shows: apart, with no call on or ringing. */
export function canCall(where: WhereState | undefined): boolean {
  return !!where && where.state === 'apart' && where.call?.status !== 'ringing'
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

/** Whether the chat is a phone call now: replies are spoken, so bursts stop, and a reply read aloud plays by itself. */
export function onCall(where: WhereState | undefined): boolean {
  return where?.state === 'call'
}

/** Together or on a call: texting habits like bursts stop. */
export function notTexting(where: WhereState | undefined): boolean {
  return inPerson(where) || onCall(where)
}

/** The Getting together slider's steps (Settings > Realism, companion/life/together.py). */
export const TOGETHER_LEVELS = [
  { label: 'Only when you ask', hint: 'They never suggest meeting up, ask you over or call on their own. Ask them and they still come or pick up when they can.' },
  { label: 'Now and then', hint: 'Once in a while they suggest meeting up, ask you over or call. Nobody turns up at your door unannounced.' },
  { label: 'True to life', hint: 'They suggest meeting up, ask you over and call about as often as real friends do (more when they live far away), and someone close who lives nearby sometimes knocks unannounced. Never in your quiet hours.' },
  { label: 'Often', hint: 'They want to see and hear from you a lot: plans most weeks, invitations over, calls, and close companions in your city dropping by more often. Never in your quiet hours.' },
]
