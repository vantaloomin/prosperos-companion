import type { FeedPage, FeedPost, Reaction } from '../../types'

export const REACTIONS: { id: Reaction; emoji: string; label: string }[] = [
  { id: 'heart', emoji: '❤️', label: 'Love' },
  { id: 'laugh', emoji: '😄', label: 'Laugh' },
  { id: 'wow', emoji: '😮', label: 'Wow' },
  { id: 'sad', emoji: '😢', label: 'Sad' },
  { id: 'hug', emoji: '🤗', label: 'Hug' },
]

/** Pages joined newest first, without repeats if a post moved between pages. */
export function joinPages(pages: FeedPage[]): FeedPost[] {
  const seen = new Set<string>()
  return pages.flatMap((page) => page.posts).filter((post) => !seen.has(post.id) && seen.add(post.id))
}

/** Tapping the current reaction clears it. */
export function nextReaction(current: Reaction | null, chosen: Reaction): Reaction | null {
  return current === chosen ? null : chosen
}

/**
 * Collects posts the reader actually saw and sends them in one batch, so opening the feed never
 * marks everything read and a new post never disappears from unread unseen.
 */
export class ReadBatcher {
  private pending = new Set<string>()
  private timer: ReturnType<typeof setTimeout> | null = null
  private send: (ids: string[]) => void
  private delay: number

  constructor(send: (ids: string[]) => void, delay = 800) {
    this.send = send
    this.delay = delay
  }

  saw(id: string) {
    this.pending.add(id)
    this.timer ??= setTimeout(() => this.flush(), this.delay)
  }

  flush() {
    if (this.timer) clearTimeout(this.timer)
    this.timer = null
    if (this.pending.size) this.send([...this.pending])
    this.pending.clear()
  }
}

/**
 * Seen once half the post was on screen, or, for a post taller than the screen (a picture and a long run of
 * comments on a phone), once it filled half the screen: such a post can never be half on screen at once.
 */
/** Steps the screen checks at, so a tall post is checked again as more of it comes on screen. */
export const SEEN_STEPS = Array.from({ length: 11 }, (_, step) => step / 20)

export function seenEnough(ratio: number, shownHeight: number, screenHeight: number): boolean {
  return ratio >= 0.5 || (screenHeight > 0 && shownHeight >= screenHeight / 2)
}

/** The newest post not yet seen, or null. */
export function firstUnread(posts: FeedPost[]): FeedPost | null {
  return posts.find((post) => !post.read) ?? null
}

/**
 * A post can be written after newer ones were already read: a friend's quiet-day post written once the day is
 * looked back on lands below them by its own date. Going to it means finding it, page by page if need be.
 * 'show' scrolls to it, 'more' loads older posts first, 'stop' gives up (nothing new, or too far back).
 */
export const SEEK_PAGES = 10

export function seekStep(posts: FeedPost[], pages: number, more: boolean): 'show' | 'more' | 'stop' {
  if (firstUnread(posts)) return 'show'
  return more && pages < SEEK_PAGES ? 'more' : 'stop'
}

/** Today's "new in Feed" button asks the feed to open at the newest post not yet seen. Read once. */
let wantsNew = false
export function askForNew() { wantsNew = true }
export function takeAskForNew(): boolean {
  const asked = wantsNew
  wantsNew = false
  return asked
}

/** A post not yet seen sits below ones already seen: easy to miss, so the feed offers a link to it. */
export function newBelow(posts: FeedPost[], unread: number): boolean {
  return unread > 0 && posts.length > 0 && posts[0].read
}
