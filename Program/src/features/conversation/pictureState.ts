// Pictures you send in chat (companion/pictures.py). The browser shrinks each one before upload; this is
// the logic around it, kept free of browser APIs so it can be tested.
import type { SentPicture } from '../../types'

/** The longest side a sent picture keeps: enough for vision models, small enough to upload quickly. */
export const MAX_SIDE = 1568
export const PER_MESSAGE = 4

export function fitWithin(width: number, height: number, max = MAX_SIDE): { width: number; height: number } {
  const scale = Math.min(1, max / Math.max(width, height))
  return { width: Math.max(1, Math.round(width * scale)), height: Math.max(1, Math.round(height * scale)) }
}

/** The out-of-character note under a picture the companion could not see, with the real reason. */
export function pictureNote(picture: SentPicture, name: string): string | null {
  if (picture.status !== 'unseen') return null
  return `${name} couldn't see this picture: ${picture.reason ?? 'it could not be described.'}`
}

export function canSend(text: string, pictures: number, busy: boolean): boolean {
  return !busy && (!!text.trim() || pictures > 0)
}
