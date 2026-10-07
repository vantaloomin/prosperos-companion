import type { CastMember } from '../../types'

/** "Stepped back on 5 October" for a companion who is not the main character. */
export function steppedBack(member: Pick<CastMember, 'stepped_back_at'>): string {
  if (!member.stepped_back_at) return ''
  return `Stepped back on ${new Date(member.stepped_back_at).toLocaleDateString(undefined, { day: 'numeric', month: 'long' })}`
}

/** The townsperson's given name, for buttons: "Make Dana the main character". */
export function givenName(full: string): string {
  return full.trim().split(/\s+/)[0] ?? full
}

/** What the townsfolk choice means for this companion, and what changing it does. */
export function townSeedText(name: string, own: boolean): { about: string; warning: string } {
  return {
    about: own
      ? `${name} has townsfolk of their own: the people at the city's places and in its neighborhoods were drawn just for ${name}.`
      : `${name}'s city has the same townsfolk as anyone else's copy of it. Seed new townsfolk to give ${name} different people around town.`,
    warning: `Everyone ${name} has met around town becomes someone ${name} never met, so ${name} starts getting to know people again. Earlier diary entries keep the names they had.`,
  }
}
