import { appDate } from '../../appTime.ts'
import { useEffect, useState } from 'react'

export function localTime(timezone: string, now: Date) {
  try {
    return new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit', weekday: 'short', timeZone: timezone }).format(now)
  } catch { return null }
}

/** The time where the companion lives, kept current while it is on screen. */
export function useLocalTime(timezone: string) {
  const [now, setNow] = useState(() => appDate())
  useEffect(() => { const timer = window.setInterval(() => setNow(appDate()), 30_000); return () => window.clearInterval(timer) }, [])
  return localTime(timezone, now)
}
