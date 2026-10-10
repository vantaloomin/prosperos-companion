import type { Looks } from '../../types'

export type LooksWord = 'build' | 'skin' | 'face' | 'jaw' | 'nose' | 'eyes' | 'eye_shape' | 'hair' | 'facial_hair' | 'feature'

export function emptyLooks(): Looks {
  return { age: null, height_cm: null, weight_kg: null, build: '', skin: '', face: '', jaw: '', nose: '', eyes: '', eye_shape: '', hair: '', facial_hair: '', feature: '' }
}

export const looksWords: { field: LooksWord; label: string }[] = [
  { field: 'build', label: 'Build' }, { field: 'skin', label: 'Skin tone' }, { field: 'face', label: 'Face shape' },
  { field: 'jaw', label: 'Jaw and chin' }, { field: 'nose', label: 'Nose' }, { field: 'eyes', label: 'Eye colour' },
  { field: 'eye_shape', label: 'Eye shape' }, { field: 'hair', label: 'Hair' }, { field: 'facial_hair', label: 'Facial hair' },
  { field: 'feature', label: 'Something people notice' },
]

/** 5'7" (170 cm): both units, since the app is used on both sides of the Atlantic. */
export function heightLabel(cm: number): string {
  const inches = Math.round(cm / 2.54)
  return `${Math.floor(inches / 12)}'${inches % 12}" (${cm} cm)`
}

export function weightLabel(kg: number): string {
  return `${Math.round(kg * 2.20462)} lb (${kg} kg)`
}

/** The choices each number offers, inside what the server accepts: ages 18 to 90, heights by the inch from 4'6" to 7'2", weights every 5 lb from 80 to 400. */
export function numberChoices(kind: 'age' | 'height' | 'weight'): number[] {
  if (kind === 'age') return Array.from({ length: 73 }, (_, index) => 18 + index)
  if (kind === 'height') return Array.from({ length: 33 }, (_, index) => Math.round((54 + index) * 2.54))
  return Array.from({ length: 65 }, (_, index) => Math.round((80 + index * 5) / 2.20462))
}
