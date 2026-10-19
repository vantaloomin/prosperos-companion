/** Wording for Loss and grief (companion/life/loss.py): the Realism switch and slider, and the circle list. */

/** The Loss slider's steps (life_settings.loss), while People can pass away is on. */
export const LOSS_LEVELS = [
  { label: 'Rare', hint: 'Hardly ever, and almost only the very old.' },
  { label: 'Now and then', hint: 'Less often than in real life, mostly the old.' },
  { label: 'True to life', hint: 'About as often as in real life: mostly the old, more after a long illness, very rarely someone young.' },
  { label: 'Often', hint: 'More often than in real life, still mostly the old.' },
]

export const PASS_AWAY_HINT = 'Someone in their life or their town can pass away, mostly the old. Their companion grieves for weeks, there is a funeral you can go to, and the date stays an anniversary. Never a companion, never a child, and never someone you wrote into a character unless you say they can on the people list.'

export const PASS_AWAY_TIP = 'Bring anyone back from the people list on Today, or make it go another way under Hidden values.'

/** "Passed away on Friday, 9 October 2026." */
export function lateText(died: string): string {
  const day = new Date(`${died}T12:00:00`)
  return `Passed away on ${day.toLocaleDateString('en-US', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}.`
}
