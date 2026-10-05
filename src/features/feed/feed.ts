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
