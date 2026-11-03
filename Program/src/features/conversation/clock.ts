import { appDate } from '../../appTime.ts'
import { useEffect, useState } from 'react'

export function localTime(timezone: string, now: Date) {
  try {
    return new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit', weekday: 'short', timeZone: timezone }).format(now)
  } catch { return null }
}

const dayIn = (now: Date, timeZone?: string) => new Intl.DateTimeFormat('en-CA', { year: 'numeric', month: '2-digit', day: '2-digit', timeZone }).format(now)

/** The phone's short time: "9:51 PM", with the weekday only when their day is not yours ("Mon 9:51 PM"). */
export function shortTime(timezone: string, now: Date, yourZone?: string) {
  try {
    const sameDay = dayIn(now, timezone) === dayIn(now, yourZone)
    return new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit', weekday: sameDay ? undefined : 'short', timeZone: timezone }).format(now)
  } catch { return null }
}

/** The time where the companion lives, kept current while it is on screen. `short` is the phone's form. */
export function useLocalTime(timezone: string, short = false) {
  const [now, setNow] = useState(() => appDate())
  useEffect(() => { const timer = window.setInterval(() => setNow(appDate()), 30_000); return () => window.clearInterval(timer) }, [])
  return short ? shortTime(timezone, now) : localTime(timezone, now)
}
