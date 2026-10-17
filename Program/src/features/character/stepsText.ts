import type { MovingIn, Newcomer, StepsView } from '../../types'
import { firstName } from './panelText.ts'
import { namesText } from '../groups/groupText.ts'

export const STEPS_KEY = ['steps']

/** The Relationship pace slider's steps (companion/life/steps.py WHEN and Step.after). */
export const PACE_LEVELS = [
  { label: 'Only when you bring it up', hint: 'They never bring up the next step on their own. You can still ask, and they answer the way they feel.' },
  { label: 'Slow', hint: 'Months between steps, and they wait until they are sure. A first "I love you" takes a while.' },
  { label: 'True to life', hint: 'About how it goes for most people: exclusive after a month or so, "I love you" a couple of months later, then meeting their people and a key to their place.' },
  { label: 'Fast', hint: 'Once you are close, things move quickly: weeks between steps, not months.' },
]

type Reached = NonNullable<StepsView['steps']>[number]
type Ask = NonNullable<StepsView['asks']>[number]

/** Who moved it to a step, after its date. */
export function howText(how: Reached['how'], name: string): string {
  const who = firstName(name)
  return {
    start: 'where the app started you', history: 'from how you know each other', them: `${who} brought it up`,
    you: 'you brought it up', set: 'you set it', confession: `${who} told you how they felt`,
  }[how]
}

/** "Mira brought up being exclusive. You said yes." / "You brought up a key to their place. Mira said not yet." */
export function askText(ask: Ask, name: string): string {
  const who = firstName(name)
  if (ask.step === 'confession') {
    if (ask.side === 'them') return `${who} told you how they feel. ${ask.status === 'yes' ? 'You said you feel the same.' : ask.status === 'no' ? 'You said you would rather stay friends.' : ask.status === 'open' ? 'Waiting on your answer.' : 'You let it pass.'}`
    return `You told ${who} how you feel. ${ask.status === 'yes' ? `${who} feels the same.` : `${who} would rather stay friends.`}`
  }
  if (ask.side === 'them') {
    const answer = { open: 'Waiting on your answer.', yes: 'You said yes.', not_yet: 'You said not yet.', no: 'You said no.', lapsed: 'You let it pass for now.' }[ask.status]
    return `${who} brought up ${ask.topic.replace(/\byour\b/, 'their')}. ${answer}`
  }
  return `You brought up ${ask.topic.replace(/\byour\b/, 'their')}. ${ask.status === 'yes' ? `${who} said yes.` : `${who} said not yet.`}`
}

/** "Oct 11, 2026", from a date, as dates read elsewhere in the app; it never breaks across lines. */
export function stepDate(day: string): string {
  return new Date(`${day}T12:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
    .replace(/ /g, '\u00a0')
}

/** "Mira plans to bring up meeting their people around Oct 28, 2026." */
export function plannedText(planned: NonNullable<StepsView['planned']>, name: string): string {
  const who = firstName(name)
  const what = planned.step === 'confession' ? 'tell you how they feel' : `bring up ${planned.topic.replace(/\byour\b/, 'their')}`
  return `${who} plans to ${what} around ${stepDate(planned.due_on)}.`
}

/** Moving in together, in one line: "Mira is moving into your place on Oct 28, 2026.", "Living together since Nov 2,
 * 2026, at a two-bedroom in Canton.", "Mira asked you to move to Chicago. It's your call: change your home city when
 * you're ready." */
export function movingText(moving: MovingIn, name: string): string {
  const who = firstName(name)
  const others = namesText(moving.with ?? [])
  if (moving.status === 'moved') return `Since ${stepDate(moving.moved_on ?? '')}${moving.home ? `, ${moving.home}` : ''}${others ? `, with ${others}` : ''}.`
  if (moving.joins) return joiningText(moving, who, others)
  // The Character page links "Change your home city" after this.
  if (moving.status === 'waiting') return `${who} asked you to move to ${moving.city} to live together.`
  const on = moving.move_on ? ` on ${stepDate(moving.move_on)}` : ''
  const where = moving.place ? ` in ${moving.place}` : ''
  return {
    yours: `${who} is moving into your place${on}.`, theirs: `You're moving into ${who}'s place${on}.`,
    new: `Moving into a new place${where}${on}.`, them: `${who} is moving to ${moving.city} to live with you${on}.`,
    you: '',
  }[moving.plan]
}

/** Sharing a home: "Theo is moving in with you and Mira on Nov 1, 2026.", or why it waits. */
function joiningText(moving: MovingIn, who: string, others: string): string {
  if (moving.status === 'moving') return `${who} is moving in with you and ${others}${moving.move_on ? ` on ${stepDate(moving.move_on)}` : ''}.`
  if (!moving.ready) return `${who} would like to live with you, but isn't ready to share a home with ${others} yet.`
  const waiting = moving.not_ready ?? []
  return `${who} would like to move in with you and ${others}. Waiting: ${namesText(waiting)} ${waiting.length > 1 ? "aren't" : "isn't"} ready to share your home yet.`
}

/** On the page of one living with you, another partner who would move in: "Theo is moving in too, on Nov 1, 2026."
 * or "Theo would like to move in too. Mira isn't ready to share your home yet." */
export function newcomerText(newcomer: Newcomer, name: string): string {
  const who = firstName(name)
  if (newcomer.status === 'moving') return `${newcomer.name} is moving in too${newcomer.move_on ? `, on ${stepDate(newcomer.move_on)}` : ''}.`
  const waiting = newcomer.open ? newcomer.not_ready.filter((item) => item !== who) : [who]
  const names = namesText(waiting.length ? waiting : [newcomer.name])
  return `${newcomer.name} would like to move in too. ${names} ${waiting.length > 1 ? "aren't" : "isn't"} ready to share your home yet.`
}
