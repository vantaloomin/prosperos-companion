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

/** How strongly the Like (positive dx) or Pass stamp shows, 0..1: nothing for a nudge, full well before the threshold,
 * so both stamps read at the same strength. */
export function stamp(dx: number, width: number): { like: number; pass: number } {
  const amount = Math.min(1, Math.max(0, Math.abs(dx) - NUDGE) / (threshold(width) * 0.4))
  return dx > 0 ? { like: amount, pass: 0 } : { like: 0, pass: dx < 0 ? amount : 0 }
}

/** Arrow keys answer the top card, unless the user is typing or choosing in a field. */
export function arrowWay(key: string, target: { tagName?: string; isContentEditable?: boolean } | null): SwipeWay | null {
  if (key !== 'ArrowLeft' && key !== 'ArrowRight') return null
  const tag = target?.tagName?.toLowerCase() ?? ''
  if (['input', 'select', 'textarea'].includes(tag) || target?.isContentEditable) return null
  return key === 'ArrowRight' ? 'like' : 'pass'
}

/** The line under the buttons: arrow keys on a computer, the buttons on a touch screen with no keyboard. */
export function hintText(left: number, touch: boolean, swipes: boolean): string {
  const count = left > 0 ? `${left} more after this one.` : 'The last one for now.'
  if (!swipes) return count
  return `${count} ${touch ? 'Swipe the card, or use the buttons.' : 'Drag the card, or use the arrow keys.'}`
}

/** What a screen reader hears after an answer: "Liked Ashanti. Next: Rachel, 40." */
export function answeredText(name: string, way: SwipeWay, next: string | null): string {
  return `${way === 'like' ? 'Liked' : 'Passed on'} ${name}.${next ? ` Next: ${next}.` : ''}`
}

export interface Pose { x: number; rotate: number; opacity: number; like: number; pass: number; lift: number }

/** Where the top card sits: following the drag, or flying off the way it was answered. Kept still (no slide or tilt,
 * only a fade) when the user asks for less motion. */
export function pose(dx: number, flying: SwipeWay | null, still: boolean, width: number): Pose {
  const sign = flying === 'like' ? 1 : -1
  const x = flying ? (still ? 0 : sign * width * 1.5) : dx
  const marks = flying ? { like: flying === 'like' ? 1 : 0, pass: flying === 'pass' ? 1 : 0 } : stamp(dx, width)
  const lift = flying ? 1 : Math.min(1, Math.abs(dx) / threshold(width))
  return { x, rotate: still ? 0 : tilt(x, width), opacity: flying ? 0 : 1, ...marks, lift }
}

/** What the Undo button says to a screen reader: "Undo liking Ashanti". */
export function undoLabel(name: string, way: SwipeWay): string {
  return `Undo ${way === 'like' ? 'liking' : 'passing on'} ${name}`
}
