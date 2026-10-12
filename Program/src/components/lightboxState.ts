/** One picture the lightbox can show: its full-size file, what it shows, and any captions drawn over it. */
export type Shown = { src: string; alt: string; top?: string; bottom?: string }

/** The picture after stepping by `by` from `index`, staying put at either end rather than wrapping round. */
export const stepTo = (index: number, by: number, count: number) => Math.min(Math.max(index + by, 0), Math.max(count - 1, 0))

const SWIPE = 60

/** What a finger drag on the picture means: a sideways swipe moves between pictures, a drag down closes it, like a phone's photo viewer. */
export function swipeAction(dx: number, dy: number): 'next' | 'previous' | 'close' | null {
  if (Math.abs(dx) >= SWIPE && Math.abs(dx) > Math.abs(dy)) return dx < 0 ? 'next' : 'previous'
  if (dy >= SWIPE * 1.5 && dy > Math.abs(dx)) return 'close'
  return null
}

/** The file name a saved picture gets, from what it shows. The browser adds the extension its file type calls for. */
export function saveName(alt: string) {
  return alt.replace(/[^\p{L}\p{N}]+/gu, ' ').trim().split(' ').slice(0, 8).join('-').toLowerCase() || 'picture'
}
