// Browser side of sending pictures: shrink, re-encode (which drops location and camera data) and upload.
import { upload } from '../../api'
import { fitWithin } from './pictureState'

export interface Uploaded { id: string; width: number; height: number }

/** A JPEG copy no larger than MAX_SIDE, on white so transparent pictures stay readable. */
export async function shrink(file: Blob): Promise<Blob> {
  let bitmap: ImageBitmap
  try {
    bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
  } catch {
    throw new Error('This browser could not open that picture. Try a JPEG or PNG.')
  }
  const size = fitWithin(bitmap.width, bitmap.height)
  const canvas = document.createElement('canvas')
  canvas.width = size.width
  canvas.height = size.height
  const context = canvas.getContext('2d')
  if (!context) throw new Error('This browser could not prepare the picture.')
  context.fillStyle = '#ffffff'
  context.fillRect(0, 0, size.width, size.height)
  context.drawImage(bitmap, 0, 0, size.width, size.height)
  bitmap.close()
  return new Promise((resolve, reject) => canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error('The picture could not be prepared.')), 'image/jpeg', 0.85))
}

export async function sendPicture(file: Blob): Promise<Uploaded> {
  return upload<Uploaded>('/pictures', await shrink(file), {})
}
