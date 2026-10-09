import type { Persona, PersonaGender, World } from '../../types'

export const GENDERS: [PersonaGender, string][] = [['', 'Not said'], ['woman', 'A woman'], ['man', 'A man'], ['nonbinary', 'Nonbinary']]

/** What a persona is called where it has no name yet. */
export function personaName(persona: Pick<Persona, 'name'> | null | undefined): string {
  return persona?.name.trim() || 'You'
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
  return world ? `${personaName(persona)} · ${world.name}` : personaName(persona)
}

export function initial(persona: Pick<Persona, 'name'> | null | undefined): string {
  return personaName(persona).slice(0, 1).toUpperCase()
}
