import type { TheirHours } from '../../types'

/** Minutes a zone is ahead of UTC right now (or at `at`), as the browser's clock database has it. */
export function zoneOffset(zone: string, at = new Date()): number {
  try {
    const parts = new Intl.DateTimeFormat('en-US', { timeZone: zone, hourCycle: 'h23', year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric' }).formatToParts(at)
    const part = (type: string) => Number(parts.find((item) => item.type === type)?.value ?? 0)
    const local = Date.UTC(part('year'), part('month') - 1, part('day'), part('hour'), part('minute'))
    return Math.round((local - Math.floor(at.getTime() / 60000) * 60000) / 60000)
  } catch {
    return 0
  }
}

/** Minutes their city's clock is ahead of the user's (companion/life/their_hours.py `gap`). */
export function clockGap(theirs: string, yours: string, at = new Date()): number {
  return zoneOffset(theirs, at) - zoneOffset(yours, at)
}

export function hoursText(minutes: number): string {
  const hours = Math.abs(minutes) / 60
  const shown = Number.isInteger(hours) ? String(hours) : hours.toFixed(1)
  return `${shown} ${hours === 1 ? 'hour' : 'hours'}`
}

/** "8 hours ahead of you", "3 hours behind you". */
export function gapText(gap: number): string {
  return `${hoursText(gap)} ${gap > 0 ? 'ahead of' : 'behind'} you`
}

/** Why a fitted week sits where it does, in the Character page's words (their_hours.py WHY). */
const FIT_WHY: Record<string, string> = {
  night_owl: "they're a night owl",
  early_riser: "they're an early riser",
  remote: 'they work remotely on odd hours',
  nights: 'they live by night',
}

/** "9 hours earlier so they're free on your evenings; they work remotely on odd hours". */
function fitted(hours: TheirHours): string {
  const why = FIT_WHY[hours.why] ? `; ${FIT_WHY[hours.why]}` : ''
  return `${hoursText(hours.fit)} ${hours.fit > 0 ? 'later' : 'earlier'} so they're free on your evenings${why}`
}

export interface HoursHint { hours: TheirHours; saved: TheirHours['mode']; city: string; gap: number }

const TURN_ON = ' Turn this on to put their whole day on your clock.'

/** The one paragraph under Live on my clock: what their hours are now, or what saving will do to them. */
export function hoursHint({ hours, saved, city, gap }: HoursHint): string {
  const place = city || 'their city'
  const pending = hours.mode !== saved
  if (hours.mode === 'mine') {
    const now = pending ? ' Saving moves their whole day onto your time.' : ''
    return `Their whole day runs on your time, so they're up when you are. In ${place} they keep odd hours, working remotely on yours.${now}`
  }
  if (hours.mode === 'fit') {
    const lead = pending ? (saved === 'mine' ? 'Saving moves their week back to the fitted hours, ' : 'Saving moves their week ') : 'The app moved their week '
    return `${lead}${fitted(hours)}.${TURN_ON}`
  }
  const lead = pending ? `Saving puts them back on ${place}'s clock` : `Their day runs on ${place}'s clock`
  return `${lead}, ${gapText(gap)}.${TURN_ON}`
}

/** Settings > Realism > Waking them (life_settings.waking_realism, companion/life/waking.py). */
export const WAKING_LEVELS = [
  { label: 'They never mind', hint: 'A second text, "wake up" or a call wakes them, and they answer sleepy but never put out, however often it happens.' },
  { label: 'Easygoing', hint: 'They wake for you, sleepy and short. Only night after night does it start to wear on them.' },
  { label: 'True to life', hint: 'They wake for you, groggy and a little annoyed, and may mention it in the morning. A few nights in a row and they ask you to let them sleep.' },
  { label: 'Wears thin fast', hint: 'Groggy and annoyed, and by the second or third night they are fed up and say so.' },
]
