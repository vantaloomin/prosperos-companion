import type { PersonaPet } from '../../types'
import { appDate } from '../../appTime.ts'

/** One of the user's pets being edited; `age` -1 keeps the age it has (or, for a new one, lets the app pick). */
export type PetDraft = { name: string; kind: string; looks: string; age: number; born?: string }

export const MAX_PETS = 8

export function petDrafts(pets?: PersonaPet[]): PetDraft[] {
  return (pets ?? []).map((pet) => ({ name: pet.name, kind: pet.kind, looks: pet.looks, age: -1, born: pet.born }))
}

/** The pets as saved: blank rows dropped; an age only when the user set one (else the pet keeps its birth date). */
export function petsBody(drafts: PetDraft[]): { name: string; kind: string; looks: string; age: number | null }[] {
  return drafts.filter((pet) => pet.name.trim()).map((pet) => ({
    name: pet.name.trim(), kind: pet.kind, looks: pet.looks.trim(), age: pet.age < 0 ? null : pet.age,
  }))
}

/** What leaving the age alone means: the age a saved pet has now, or one picked to fit a new pet's looks. */
export function unsetAge(pet: PetDraft, today = appDate()): string {
  if (!pet.born) return 'Picked for you'
  const years = Math.floor((today.getTime() - new Date(`${pet.born}T12:00:00`).getTime()) / (365.25 * 86400000))
  return years < 1 ? 'Under a year' : `${years} year${years === 1 ? '' : 's'} old`
}
