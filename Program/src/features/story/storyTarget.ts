/** The Story chapter to open at, set by a link from somewhere else (a companion's chat: "Read it") just before
 * going to the Story, and read once when the Story opens (src/features/story/useStoryScroll.ts). */
let chapter: number | null = null

export function openStoryAt(number: number) { chapter = number }
export function storyTarget(): number | null { return chapter }
export function clearStoryTarget() { chapter = null }
