import type { StepsView } from '../../types'
import { firstName } from './panelText.ts'

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

/** "11 October 2026", from a date. */
export function stepDate(day: string): string {
  return new Date(`${day}T12:00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'long', year: 'numeric' })
}
