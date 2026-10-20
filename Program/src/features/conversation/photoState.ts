import type { ChatPhoto, ImageStatus, Message } from '../../types'

export const isTaking = (status?: ImageStatus) => status === 'queued' || status === 'running'

const noun = (photo: ChatPhoto) => photo.kind === 'meme' ? 'meme' : photo.kind === 'selfie' ? 'selfie' : 'photo'

const LINES: Partial<Record<ImageStatus, (photo: ChatPhoto) => string>> = {
  queued: (photo) => `The ${noun(photo)} is on its way.`,
  running: (photo) => `The ${noun(photo)} is on its way…`,
  failed: (photo) => `The ${noun(photo)} couldn't be made. ${photo.error ?? ''}`.trim(),
  cancelled: (photo) => `The ${noun(photo)} was cancelled.`,
  interrupted: (photo) => `The app closed before the ${noun(photo)} was made.`,
}

/** A photo that ended without a picture: it can be made again. */
export const canRetry = (photo: ChatPhoto) => !photo.ref && (photo.status === 'failed' || photo.status === 'cancelled' || photo.status === 'interrupted')

/** The shape the chat holds for a photo while it loads: a meme is square, older photos without one are landscape. */
export const photoShape = (photo: ChatPhoto) => photo.kind === 'meme' ? 'square' : photo.aspect ?? 'landscape'

/** One plain line about a photo still coming or one that could not be made, else null. */
export function photoLine(photo: ChatPhoto): string | null {
  return LINES[photo.status]?.(photo) ?? null
}

const KINDS: Record<ChatPhoto['kind'], string> = { moment: 'Photo', selfie: 'Selfie', view: 'Photo of the view', meme: 'Meme picture' }

/** Alt text for the picture itself; a meme's captions are real text drawn over it. */
export const photoAlt = (name: string, photo: ChatPhoto) => photo.source === 'gif' ? `Reaction GIF from ${name}` : `${KINDS[photo.kind]} from ${name}: ${photo.summary}`

/** Where the picture loads from: a template's or GIF's own address, else the image job's file once it is made. */
export const photoSource = (photo: ChatPhoto, jobFile: (ref: string) => string) => photo.src ?? (photo.ref ? jobFile(photo.ref) : null)

/** The widest a meme on a template or a GIF shows, and the most room a tall one may take. */
const FITTED_WIDTH = 340
const FITTED_HEIGHT = 400

/** A template's or GIF's own shape, so the chat holds exactly its space: no wider than a square meme, no taller than a portrait photo. */
export function fittedSize(photo: ChatPhoto): { aspectRatio: string; width: string } | null {
  if (!photo.src || !photo.width || !photo.height) return null
  const width = Math.round(Math.min(FITTED_WIDTH, FITTED_HEIGHT * photo.width / photo.height))
  return { aspectRatio: `${photo.width} / ${photo.height}`, width: `min(100%, ${width}px)` }
}

/** The newest reply that sent a photo of their moment (not a meme), for the Visual novel stage's backdrop. */
export function latestPhotoId(messages: Message[]): string | null {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index]
    if (message.role === 'companion' && message.photo && message.photo.kind !== 'meme') return message.id
  }
  return null
}
