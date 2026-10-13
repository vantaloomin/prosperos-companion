/** The swipe stack's rules (Dating.tsx): how far a card has to go, or how fast, before a drag counts. */

export type SwipeWay = 'like' | 'pass'

/** How long a card takes to fly off, in ms. */
export const FLY_MS = 240
/** A drag shorter than this (px) is a tap or a wobble, never a swipe. */
const NUDGE = 24
/** A flick: fast enough (px per ms) and past the nudge counts even when short. */
const FLICK = 0.6
/** The furthest the card leans, in degrees. */
const TILT = 14

/** How far the card has to be dragged to count: a third of its width, at least 80px. */
export function threshold(width: number): number {
  return Math.max(80, width / 3)
}

/** Where a let-go card goes: right likes, left passes, anything short and slow springs back (null). */
export function decide(dx: number, velocity: number, width: number): SwipeWay | null {
  if (Math.abs(dx) < NUDGE) return null
  const far = Math.abs(dx) >= threshold(width)
  const flicked = Math.abs(velocity) >= FLICK && Math.sign(velocity) === Math.sign(dx)
  if (!far && !flicked) return null
  return dx > 0 ? 'like' : 'pass'
}

/** The card leans the way it is dragged, a little more the further it goes. */
export function tilt(dx: number, width: number): number {
  const lean = (dx / Math.max(width, 1)) * TILT * 1.5
  return Math.max(-TILT, Math.min(TILT, lean))
}

/** How strongly the Like (positive dx) or Pass stamp shows, 0..1, full at the threshold. */
export function stamp(dx: number, width: number): { like: number; pass: number } {
  const amount = Math.min(1, Math.abs(dx) / threshold(width))
  return dx > 0 ? { like: amount, pass: 0 } : { like: 0, pass: dx < 0 ? amount : 0 }
}

/** Arrow keys answer the top card, unless the user is typing or choosing in a field. */
export function arrowWay(key: string, target: { tagName?: string; isContentEditable?: boolean } | null): SwipeWay | null {
  if (key !== 'ArrowLeft' && key !== 'ArrowRight') return null
  const tag = target?.tagName?.toLowerCase() ?? ''
  if (['input', 'select', 'textarea'].includes(tag) || target?.isContentEditable) return null
  return key === 'ArrowRight' ? 'like' : 'pass'
}
