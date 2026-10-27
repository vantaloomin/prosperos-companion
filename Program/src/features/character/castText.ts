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

/** What the townsfolk choice means for this companion, and what changing it does. `notables` are the city's
 * well-known people (a pack's named characters), who are in every town. */
export function townSeedText(name: string, own: boolean, notables: string[] = []): { about: string; warning: string } {
  const stay = notablesStay(name, notables)
  return {
    about: (own
      ? `${name} has townsfolk of their own: the people at the city's places and in its neighborhoods were drawn just for ${name}.`
      : `${name}'s city has the same townsfolk as anyone else's copy of it. Seed new townsfolk to give ${name} different people around town.`) + stay,
    warning: notables.length
      ? `Everyone ${name} has met around town becomes someone ${name} never met, so ${name} starts getting to know people again. The city's well-known people stay, and ${name} still knows the ones they've met. Earlier diary entries keep the names they had.`
      : `Everyone ${name} has met around town becomes someone ${name} never met, so ${name} starts getting to know people again. Earlier diary entries keep the names they had.`,
  }
}

/** " Ahri, Akali and 24 other well-known people are there, whatever townsfolk Sett has." */
function notablesStay(name: string, notables: string[]): string {
  if (notables.length === 0) return ''
  const [first, second, third] = notables
  const who = notables.length === 1 ? `${first} is`
    : notables.length === 2 ? `${first} and ${second} are`
      : notables.length === 3 ? `${first}, ${second} and ${third} are`
        : `${first}, ${second} and ${notables.length - 2} other well-known people are`
  return ` ${who} there, whatever townsfolk ${name} has.`
}
