import type { BackWhenMoment, BackWhenMoments } from '../../types'

/** The sheet's choice: one of the app's moments, or a year the user picks. */
export type BackWhenPick = { kind: 'moment'; key: string } | { kind: 'year' }

/** The app's pick, ready when the sheet opens: its first moment, or a year of the user's own when it found none. */
export function firstPick(data: Pick<BackWhenMoments, 'moments'>): BackWhenPick {
  return data.moments.length ? { kind: 'moment', key: data.moments[0].key } : { kind: 'year' }
}

/** The year picker's first year: the middle of what is allowed, so it isn't simply the latest. */
export function firstYear(data: Pick<BackWhenMoments, 'earliest' | 'latest'>): number {
  return Math.round((data.earliest + data.latest) / 2)
}

/** Every year the user can pick, latest first. */
export function backWhenYears(data: Pick<BackWhenMoments, 'earliest' | 'latest'>): number[] {
  return Array.from({ length: Math.max(data.latest - data.earliest + 1, 0) }, (_, index) => data.latest - index)
}

export function pickedYear(data: Pick<BackWhenMoments, 'moments'>, pick: BackWhenPick, year: number): number {
  return pick.kind === 'moment' ? data.moments.find((moment) => moment.key === pick.key)?.year ?? year : year
}

/** Under a moment: "2009 · Dana was 24". A round age names the age already, so it says the year alone. */
export function momentLine(moment: BackWhenMoment, name: string): string {
  const first = name.trim().split(/\s+/)[0] || name
  return moment.age === null || moment.key.startsWith('age:') ? String(moment.year) : `${moment.year} · ${first} was ${moment.age}`
}

/** What going back does, said once above the choices. */
export function backWhenNote(name: string): string {
  return `A new world opens in that year with ${name}, in the same town with the same people, everyone younger. What happens there stays there, and this world stays as it is. Switch between them under Worlds.`
}

export const HISTORY_HINT = 'Off, the two of you meet as strangers. On, you start wherever the two of you were that year, and as strangers before the day you met.'
