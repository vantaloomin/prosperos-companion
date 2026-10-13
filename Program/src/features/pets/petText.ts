import type { PetView } from '../../types'

export const PETS_KEY = ['pets']

/** "Pepper, a beagle mix with floppy ears, 4 years old" for a pet in someone's profile. */
export function petLine(pet: PetView): string {
  if (pet.state === 'died') return `${pet.name}, ${pet.looks}, is remembered fondly`
  return `${pet.name}, ${pet.looks}, ${pet.age}`
}

/** The hidden numbers behind a pet (Settings > Realism > Hidden values), or '' when they are hidden. */
export function petNumbers(pet: PetView): string {
  if (pet.health === null || pet.lifespan_years === null) return ''
  return `Health ${pet.health} of 100 · usually lives about ${pet.lifespan_years} years`
}

/** "Mar 4" for a date in a pet's recent history. */
export function petDate(value: string): string {
  return new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

/** A sentence with a capital and a full stop. */
export function sentenceOf(text: string): string {
  const trimmed = text.trim()
  if (!trimmed) return ''
  return `${trimmed.charAt(0).toUpperCase()}${trimmed.slice(1)}${/[.!?]$/.test(trimmed) ? '' : '.'}`
}

/** The kinds a user can give their own pets, as companion/life/data/pets.json names them. */
export const PET_KINDS: { id: string; label: string }[] = [
  { id: 'cat', label: 'Cat' }, { id: 'dog', label: 'Dog' }, { id: 'rabbit', label: 'Rabbit' }, { id: 'bird', label: 'Songbird' },
  { id: 'parrot', label: 'Parrot' }, { id: 'fish', label: 'Fish' }, { id: 'hamster', label: 'Hamster' }, { id: 'guinea-pig', label: 'Guinea pig' },
  { id: 'ferret', label: 'Ferret' }, { id: 'lizard', label: 'Lizard' }, { id: 'snake', label: 'Snake' }, { id: 'tortoise', label: 'Tortoise' },
  { id: 'chickens', label: 'Backyard chickens' }, { id: 'horse', label: 'Horse' }, { id: 'other', label: 'Something else' },
]

/** An age the user sets with a stepper; -1 leaves it to the app (or, when editing, keeps the pet's age). */
export function ageChoice(years: number, unset = 'Picked for you'): string {
  if (years < 0) return unset
  if (years === 0) return 'Under a year'
  return `${years} year${years === 1 ? '' : 's'} old`
}

export const MAX_PET_AGE = 30
