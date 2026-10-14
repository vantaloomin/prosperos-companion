/** "0:07" for seven seconds: a voice note's length or how far it has played. */
export function clockLength(seconds: number): string {
  const whole = Math.max(0, Math.round(seconds))
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, '0')}`
}

/** On a call, a reply read aloud plays by itself only when it just arrived, not when the chat is opened later. */
export function playsByItself(arrived: string | null, now: number): boolean {
  return !!arrived && now - Date.parse(arrived) < 60_000
}
