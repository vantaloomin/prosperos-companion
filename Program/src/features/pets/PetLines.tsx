import type { PetView } from '../../types'
import { petLine, petNumbers } from './petText'

/** Someone else's pets in their profile (the circle, townsfolk): who they are and, in plain words, how they are.
 * Two or more share one "Pets ·" line (Iris, circle pets review). */
export function PetLines({ pets }: { pets?: PetView[] }) {
  if (!pets || pets.length === 0) return null
  if (pets.length > 1) return (
    <p className="subtle pet-line">
      <span className="pet-line-label">Pets ·</span> {pets.map((pet) => `${petLine(pet)}${pet.status && pet.state !== 'died' ? ` (${pet.status.replace(/\.$/, '')})` : ''}`).join('; ')}.
    </p>
  )
  return <>{pets.map((pet) => (
    <p key={pet.key} className="subtle pet-line">
      <span className="pet-line-label">Pet ·</span> {petLine(pet)}.{pet.status ? ` ${pet.status}` : ''}
      {petNumbers(pet) && <span className="pet-numbers"> {petNumbers(pet)}.</span>}
    </p>
  ))}</>
}
