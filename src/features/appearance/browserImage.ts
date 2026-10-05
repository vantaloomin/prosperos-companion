// Canvas helpers for reference pictures. They run only in the browser; the logic they rely on is in loraState.ts.
import type { Crop } from '../../types'
import { cropPixels, dhash, grayscale } from './loraState'

/** The difference hash of a picture, or undefined when the browser cannot decode it. */
export async function hashPicture(file: Blob): Promise<string | undefined> {
  try {
    const bitmap = await createImageBitmap(file)
    const canvas = document.createElement('canvas')
    canvas.width = 9
    canvas.height = 8
    const context = canvas.getContext('2d')
    if (!context) return undefined
    context.drawImage(bitmap, 0, 0, 9, 8)
    bitmap.close()
    return dhash(grayscale(context.getImageData(0, 0, 9, 8).data))
  } catch {
    return undefined
  }
}

/** A cropped copy of the picture at `url`, in the same format. The original is untouched. */
export async function cropCopy(url: string, crop: Crop, type: string): Promise<Blob> {
  const bitmap = await createImageBitmap(await (await fetch(url)).blob())
  const area = cropPixels(crop, bitmap.width, bitmap.height)
  const canvas = document.createElement('canvas')
  canvas.width = area.width
  canvas.height = area.height
  canvas.getContext('2d')?.drawImage(bitmap, area.x, area.y, area.width, area.height, 0, 0, area.width, area.height)
  bitmap.close()
  return new Promise((resolve, reject) => canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error('The crop could not be made.')), type, 0.95))
}

/** A PNG copy of a picture the trainer cannot read (WebP), at the same size. */
export async function pngCopy(blob: Blob): Promise<Blob> {
  const bitmap = await createImageBitmap(blob)
  const canvas = document.createElement('canvas')
  canvas.width = bitmap.width
  canvas.height = bitmap.height
  canvas.getContext('2d')?.drawImage(bitmap, 0, 0)
  bitmap.close()
  return new Promise((resolve, reject) => canvas.toBlob((copy) => copy ? resolve(copy) : reject(new Error('The picture could not be converted.')), 'image/png'))
}
