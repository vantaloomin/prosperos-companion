import type { PetView } from '../../types'
import { petLine, petNumbers } from './petText'

/** Someone else's pets in their profile (the circle, townsfolk): who they are and, in plain words, how they are. */
export function PetLines({ pets }: { pets?: PetView[] }) {
  if (!pets || pets.length === 0) return null
  return <>{pets.map((pet) => (
    <p key={pet.key} className="subtle pet-line">
      <span className="pet-line-label">Pet ·</span> {petLine(pet)}.{pet.status ? ` ${pet.status}` : ''}
      {petNumbers(pet) && <span className="pet-numbers"> {petNumbers(pet)}.</span>}
    </p>
  ))}</>
}
