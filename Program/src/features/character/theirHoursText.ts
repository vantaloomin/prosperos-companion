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
  night_owl: 'a night owl',
  early_riser: 'an early riser',
  remote: 'working remotely on odd hours',
  nights: 'living by night',
}

export function fitText(hours: TheirHours): string {
  const way = hours.fit > 0 ? 'later' : 'earlier'
  const why = FIT_WHY[hours.why] ? `, ${FIT_WHY[hours.why]}` : ''
  return `The app moved their week ${hoursText(hours.fit)} ${way} than written so they are free on your evenings${why}.`
}

export function mineHint(city: string, gap: number, on: boolean, saved: boolean): string {
  const place = city || 'their city'
  if (on) {
    const now = saved ? '' : ' Saving moves their week.'
    return `Their whole day runs on your time, so they are up when you are. In ${place} they keep odd hours, working remotely on yours.${now}`
  }
  return `Their day runs on ${place}'s clock, ${gapText(gap)}. Turn this on and save, and their whole day moves onto your time; they keep odd hours where they live.`
}

/** Settings > Realism > Waking them (life_settings.waking_realism, companion/life/waking.py). */
export const WAKING_LEVELS = [
  { label: 'They never mind', hint: 'A second text, "wake up" or a call wakes them, and they answer sleepy but never put out, however often it happens.' },
  { label: 'Easygoing', hint: 'They wake for you, sleepy and short. Only night after night does it start to wear on them.' },
  { label: 'True to life', hint: 'They wake for you, groggy and a little annoyed, and may mention it in the morning. A few nights in a row and they ask you to let them sleep.' },
  { label: 'Wears thin fast', hint: 'Groggy and annoyed, and by the second or third night they are fed up and say so.' },
]
