import type { ChatPhoto, ImageStatus, Message } from '../../types'

export const isTaking = (status?: ImageStatus) => status === 'queued' || status === 'running'

const LINES: Partial<Record<ImageStatus, (photo: ChatPhoto) => string>> = {
  queued: (photo) => photo.ref ? 'A new version of this photo is waiting to start.' : 'The photo is on its way.',
  running: (photo) => photo.ref ? 'Making a new version of this photo…' : 'The photo is on its way…',
  failed: (photo) => `The photo couldn't be made. ${photo.error ?? ''}`.trim(),
  cancelled: () => 'The photo was cancelled.',
  interrupted: () => 'The app closed before the photo was made.',
}

/** One plain line about a photo still coming or one that could not be made, else null. */
export function photoLine(photo: ChatPhoto): string | null {
  return LINES[photo.status]?.(photo) ?? null
}

export const photoAlt = (name: string, photo: ChatPhoto) => `Photo from ${name}: ${photo.summary}`

/** The newest reply that sent a photo, for the Visual novel stage's backdrop. */
export function latestPhotoId(messages: Message[]): string | null {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index]
    if (message.role === 'companion' && message.photo) return message.id
  }
  return null
}
