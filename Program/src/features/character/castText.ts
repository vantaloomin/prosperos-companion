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
