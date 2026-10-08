// Display logic for the onboarding profile pictures; no browser needed, so it is tested directly.
import type { GeneratedImage, Generation, PlannedShot } from '../../types'

export const PORTRAITS_KEY = ['lora-portraits']

/** What leaves the computer, said before anything is sent. */
export function sendsLine(planned: PlannedShot[], withoutReference: boolean): string {
  const target = planned[0]?.backend
  if (!target) return planned[0]?.refusal ?? 'These pictures cannot be made yet.'
  const where = `${target.label}${target.local ? ' on this computer' : ''}`
  if (withoutReference) return `All three go to ${where} as descriptions only, so they may not look like the same person.`
  const following = planned.filter((shot) => shot.follows !== null && shot.follows !== undefined && shot.backend).length
  if (!following) return `The picture goes to ${where}.`
  return `All three go to ${where}. Pictures 2 and 3 each send picture 1 along as the reference, so they show the same person.`
}

/** Pictures that finished and are not yet kept or discarded. */
export function keepable(set: Generation): GeneratedImage[] {
  return set.images.filter((image) => image.status === 'completed' && image.decision === null && image.has_image)
}

/** The set's state in a sentence, counting only what happened. */
export function setLine(set: Generation): string {
  if (set.status === 'running') {
    const next = set.images.find((image) => image.status === 'running' || image.status === 'queued')
    return next ? `Making picture ${next.position + 1} of ${set.images.length}: ${next.label.toLowerCase()}.` : 'Finishing.'
  }
  if (set.images.every((image) => image.decision === 'kept' || image.status !== 'completed') && set.counts.kept) {
    return `Kept ${set.counts.kept} picture${set.counts.kept === 1 ? '' : 's'}.`
  }
  const failed = set.images.filter((image) => image.status !== 'completed').length
  if (!failed) return 'All three are ready. Make any of them again if you like.'
  return `${set.counts.completed} made, ${failed} not made. Make the missing ones again if you like.`
}

/** Remaking the profile picture remakes the others too, since both are made from it. */
export function redoLabel(image: GeneratedImage, images: GeneratedImage[]): string {
  return images.some((other) => other.follows === image.position) ? 'Make this and the pictures made from it again' : 'Make this one again'
}

/** A picture can be made again while neither it nor any picture made from it has been kept. */
export function redoable(image: GeneratedImage, images: GeneratedImage[]): boolean {
  return [image, ...images.filter((other) => other.follows === image.position)].every((item) => item.decision === null)
}

/** What a picture without a file says instead. */
export function cardNote(image: GeneratedImage): string {
  if (image.error) return image.error
  if (image.status === 'queued') return image.follows !== null && image.follows !== undefined ? `Waiting for picture ${image.follows + 1}.` : 'Waiting to start.'
  return image.status === 'running' ? 'Being made…' : image.status
}

export function madeBy(image: GeneratedImage): string {
  const follows = image.follows ?? null
  return `${image.backend_label ?? ''}${follows === null ? '' : `, from picture ${follows + 1}`}`
}
