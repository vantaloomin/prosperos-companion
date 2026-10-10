import type { Persona, PersonaGender, World } from '../../types'

export const GENDERS: [PersonaGender, string][] = [['', 'Not said'], ['woman', 'A woman'], ['man', 'A man'], ['nonbinary', 'Nonbinary']]

/** A persona's own name, or '' when the user has not given one. The app never makes one up (Vanta, 2026-10-09). */
export function personaName(persona: Pick<Persona, 'name'> | null | undefined): string {
  return persona?.name.trim() ?? ''
}

/** How a persona is named on Worlds: their name, or a description of them while they have none (Iris). */
export function personaTitle(persona: Pick<Persona, 'name'>): string {
  return personaName(persona) || 'Your first persona'
}

/** A persona referred to inside a sentence or button: "New world for Sam", "New world for this persona". */
export function personaRef(persona: Pick<Persona, 'name'>): string {
  return personaName(persona) || 'this persona'
}

/** "Mira and Sally", "Mira, Sally and 2 more", or that nobody lives there yet. */
export function companionsLine(world: Pick<World, 'companions'>): string {
  const names = world.companions
  if (!names.length) return 'No companions yet'
  if (names.length === 1) return names[0]
  if (names.length <= 3) return `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`
  return `${names.slice(0, 2).join(', ')} and ${names.length - 2} more`
}

/** The label under the nav button: who the user is and where. */
export function whereLine(persona: Pick<Persona, 'name'> | null | undefined, world: Pick<World, 'name'> | null | undefined): string {
  const name = personaName(persona)
  if (!world) return name
  return name ? `${name} · ${world.name}` : world.name
}

export function initial(persona: Pick<Persona, 'name'> | null | undefined): string {
  return personaName(persona).slice(0, 1).toUpperCase()
}
