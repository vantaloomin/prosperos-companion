import { useEffect, useRef, useState } from 'react'
import type { FeedPage, FeedPost } from '../../types'
import { reducedMotion } from '../../motion'
import { firstUnread, newBelow, seekStep, takeAskForNew } from './feedState'

type Pages = { isSuccess: boolean; isFetchingNextPage: boolean; hasNextPage: boolean; data?: { pages: FeedPage[] }; fetchNextPage: () => Promise<unknown> }

/**
 * Going to the newest post not yet seen, wherever its date puts it: older pages load until it is there, then it
 * scrolls into view. Asked for by Today's "new in Feed" button (askForNew) or the feed's own link (`seek`), offered
 * when a new post sits below ones already seen and the whole feed is on show (`everything`): the count is the whole feed's. `offer` is how many to name, or 0.
 */
export function useSeekNew(feed: Pages, posts: FeedPost[], everything: boolean): { offer: number; seek: () => void } {
  const unread = feed.data?.pages[0]?.unread ?? 0
  const seeking = useRef(false)
  const [asked, setAsked] = useState(0)
  const pages = feed.data?.pages.length ?? 0
  useEffect(() => {
    if (takeAskForNew()) seeking.current = true
    if (!seeking.current || !feed.isSuccess || feed.isFetchingNextPage) return
    const step = unread ? seekStep(posts, pages, feed.hasNextPage) : 'stop'
    if (step === 'more') { void feed.fetchNextPage(); return }
    seeking.current = false
    const found = firstUnread(posts)
    // The top post needs no scrolling to.
    if (step === 'show' && found && found !== posts[0]) showPost(found.id)
  }, [feed, posts, pages, unread, asked])
  return { offer: everything && newBelow(posts, unread) ? unread : 0, seek: () => { seeking.current = true; setAsked((count) => count + 1) } }
}

/** The post's card scrolls to the top of the screen. */
function showPost(id: string) {
  const card = document.getElementById(`post-${id}`)?.closest('article')
  if (!card) return
  card.scrollIntoView({ behavior: reducedMotion() ? 'auto' : 'smooth', block: 'start' })
  // Focus follows, for a keyboard or screen reader; a soft highlight shows where it landed (none with reduced motion).
  card.focus({ preventScroll: true })
  if (!reducedMotion()) {
    card.classList.add('arrived')
    window.setTimeout(() => card.classList.remove('arrived'), 1500)
  }
  // Pictures above it can still be loading and push it down; once they have, it comes back to the top.
  window.setTimeout(() => {
    const top = card.getBoundingClientRect().top
    if (top < 0 || top > window.innerHeight / 3) card.scrollIntoView({ block: 'start' })
  }, 900)
}
