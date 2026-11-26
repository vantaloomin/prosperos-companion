import { useEffect, useRef, type RefObject } from 'react'
import { clearStoryTarget, storyTarget } from './storyTarget'

/** Put a chapter's heading at the top of the page. A story with one chapter has no heading, so it opens at its
 * first line. */
function showChapter(chapter: number, end: HTMLElement | null) {
  const heading = document.getElementById(`story-chapter-${chapter}`)
  if (heading) heading.scrollIntoView({ block: 'start' })
  else end?.parentElement?.scrollTo({ top: 0 })
}

/** Where the story's page rests: at its end, following new lines, unless it was opened at a chapter ("Read it" in a
 * companion's chat), which then stands at the top until something new is written. */
export function useStoryScroll(end: RefObject<HTMLElement | null>, lines: number, changed: unknown) {
  const target = useRef(storyTarget())
  const openedAt = useRef(lines)
  useEffect(() => {
    clearStoryTarget()
    if (target.current !== null && openedAt.current === lines) showChapter(target.current, end.current)
    else end.current?.scrollIntoView?.({ block: 'end' })
  }, [end, lines, changed])
}
