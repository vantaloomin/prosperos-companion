import { useLayoutEffect, type RefObject } from 'react'

const GUTTER = 8

/** How far to move a box sideways so all of it sits inside a window `width` wide, with a small gutter. */
export function shiftToFit(left: number, right: number, width: number): number {
  if (right > width - GUTTER) return Math.max(GUTTER - left, width - GUTTER - right)
  if (left < GUTTER) return GUTTER - left
  return 0
}

/**
 * Keeps a pop-over (a tip, a menu panel) wholly on screen while it is open: near the edge of a phone it moves
 * sideways instead of running off it. It sets `--fit-shift`, which the pop-over's CSS adds to its transform.
 */
export function useFitOnScreen(ref: RefObject<HTMLElement | null>, open: boolean) {
  useLayoutEffect(() => {
    const element = ref.current
    if (!open || !element) return
    const fit = () => {
      element.style.setProperty('--fit-shift', '0px')
      const box = element.getBoundingClientRect()
      element.style.setProperty('--fit-shift', `${shiftToFit(box.left, box.right, window.innerWidth)}px`)
    }
    fit()
    window.addEventListener('resize', fit)
    return () => window.removeEventListener('resize', fit)
  }, [ref, open])
}
