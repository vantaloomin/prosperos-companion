/** Status messages (companion/life/status.py): what shows, kept apart from the components for tests. */

export type AwayGlyph = 'moon' | 'briefcase' | 'pin'
export interface CompanionStatus { text: string; set_by: 'app' | 'you'; away: { text: string; glyph: AwayGlyph } | null }

/** The away line while they are asleep, at work or out, else their status. */
export function shown(status: CompanionStatus | null | undefined): { text: string; away: AwayGlyph | null } | null {
  if (!status) return null
  return status.away ? { text: status.away.text, away: status.away.glyph } : status.text ? { text: status.text, away: null } : null
}

/** For screen readers: "Maya's status: at work till 6". */
export function statusLabel(name: string, status: CompanionStatus | null | undefined): string {
  const line = shown(status)
  return line ? `${name}'s status: ${line.text}` : ''
}

/** The hint under the field while the user edits it. */
export function stickHint(name: string): string {
  return `Stays until something big happens in ${name}'s life. Leave it empty and ${name} picks one.`
}
