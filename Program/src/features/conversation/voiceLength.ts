/** "0:07" for seven seconds: a voice note's length or how far it has played. */
export function clockLength(seconds: number): string {
  const whole = Math.max(0, Math.round(seconds))
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, '0')}`
}
