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

/** Which worlds a persona lives in, said only when another persona has the same name (Iris): "Grandport", or
 * "Grandport +1" with more worlds. '' when their name is theirs alone. */
export function worldTag(persona: Pick<Persona, 'id' | 'name'> & { worlds: Pick<World, 'name'>[] }, personas: Pick<Persona, 'id' | 'name'>[]): string {
  const name = personaName(persona)
  const twin = personas.some((other) => other.id !== persona.id && personaName(other) === name)
  if (!twin || !persona.worlds.length) return ''
  return persona.worlds.length > 1 ? `${persona.worlds[0].name} +${persona.worlds.length - 1}` : persona.worlds[0].name
}

/** The muted words after a persona's name on Worlds: "you, now", their world when it tells two of a name apart, or
 * both ("you, now · Baltimore"). */
export function personaSuffix(active: boolean, tag: string): string {
  return [active ? 'you, now' : '', tag].filter(Boolean).join(' · ')
}

/** A persona in a sentence, with their world when another persona shares the name: "Sam (Grandport)". */
export function personaRefTagged(persona: Pick<Persona, 'name'>, tag: string): string {
  return tag ? `${personaRef(persona)} (${tag})` : personaRef(persona)
}

/** The link and form for copying a persona into a world of their own: "Copy Sam to a new world". */
export function copyLabel(persona: Pick<Persona, 'name'>): string {
  return `Copy ${personaRef(persona)} to a new world`
}

/** What a copy is, above its city picker (Iris). */
export function copyNote(persona: Pick<Persona, 'name'>): string {
  const name = personaName(persona)
  const who = name ? `this ${name}` : 'this persona'
  return `${name ? `A second ${name}` : 'A second persona'} with the same details, starting over in a new world with new people. Your companions and history stay with ${who}, and changing one later leaves the other as it is.`
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

/** A persona's age: 18 to 120, and for a long-lived kind (an elf, a dwarf) on up to 5,000 in steps that get wider
 * (5s to 500, 10s to 1,000, 50s after). A saved age off the list stays listed, so nothing changes by itself. Never
 * free text. */
export function personaAges(longLived: boolean, current: number | null): number[] {
  const ages = Array.from({ length: 103 }, (_, index) => 18 + index)
  if (longLived) {
    for (let age = 125; age <= 500; age += 5) ages.push(age)
    for (let age = 510; age <= 1000; age += 10) ages.push(age)
    for (let age = 1050; age <= 5000; age += 50) ages.push(age)
  }
  return current !== null && !ages.includes(current) ? [...ages, current].sort((a, b) => a - b) : ages
}

/** "312" or "1,050": an age in the picker. */
export function ageText(age: number): string {
  return age.toLocaleString('en-US')
}

/** Under the age, when it is past what their kind allows: why it can't be saved. */
export function ageHint(age: number | null, longLived: boolean): string | undefined {
  if (age !== null && age > 120 && !longLived) return 'An age past 120 is only for a long-lived kind: pick one under Kind.'
  return undefined
}
