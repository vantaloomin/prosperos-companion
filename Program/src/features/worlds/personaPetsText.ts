import type { PersonaPet } from '../../types'

export type PetDraft = { name: string; kind: string; looks: string; age: string }

export const MAX_PETS = 8

export function petDrafts(pets?: PersonaPet[]): PetDraft[] {
  return (pets ?? []).map((pet) => ({ name: pet.name, kind: pet.kind, looks: pet.looks, age: '' }))
}

/** The pets as saved: blank rows dropped; an age only when the user typed one (else the pet keeps its birth date). */
export function petsBody(drafts: PetDraft[]): { name: string; kind: string; looks: string; age: number | null }[] {
  return drafts.filter((pet) => pet.name.trim()).map((pet) => ({
    name: pet.name.trim(), kind: pet.kind, looks: pet.looks.trim(), age: pet.age === '' ? null : Number(pet.age),
  }))
}

export function petsValid(drafts: PetDraft[]): boolean {
  return drafts.every((pet) => pet.age === '' || (Number.isInteger(Number(pet.age)) && Number(pet.age) >= 0 && Number(pet.age) <= 90))
}
