import { useSyncExternalStore } from 'react'
import { appNow } from '../appTime.ts'
import { clockTime, exactTime, relativeTime } from '../when.ts'

// One timer for every timestamp on screen: each re-renders only when its minute changes.
const listeners = new Set<() => void>()
let timer: number | undefined
let minute = Math.floor(appNow() / 60_000)

function tick() {
  const next = Math.floor(appNow() / 60_000)
  if (next === minute) return
  minute = next
  listeners.forEach((listener) => listener())
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  if (timer === undefined) timer = window.setInterval(tick, 10_000)
  return () => {
    listeners.delete(listener)
    if (!listeners.size) { window.clearInterval(timer); timer = undefined }
  }
}

/** The app's time to the minute, kept current while anything shows it. */
function useAppMinute(): number {
  return useSyncExternalStore(subscribe, () => minute, () => minute) * 60_000
}

/**
 * A timestamp: "5 minutes ago" and the like, with the exact date and time on hover. `clock` shows the clock
 * time instead, with the date once it is not today (Retro IM's "[9:14 PM]").
 */
export function Stamp({ value, clock = false, className }: { value: string; clock?: boolean; className?: string }) {
  useAppMinute()
  const now = appNow()
  return <time className={className} dateTime={value} title={exactTime(value)}>{clock ? clockTime(value, now) : relativeTime(value, now)}</time>
}
