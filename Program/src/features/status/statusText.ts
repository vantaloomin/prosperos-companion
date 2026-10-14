/** Status messages (companion/life/status.py): what shows, kept apart from the components for tests. */

export type AwayGlyph = 'moon' | 'briefcase' | 'pin' | 'phone' | 'luggage'
/** Together or apart (companion/life/together.py), or on a call (companion/life/calls.py), in plain words; the text is empty while apart in the same city. */
export interface StatusWhere { state: 'together' | 'apart' | 'call'; kind: string; text: string }
export interface CompanionStatus { text: string; set_by: 'app' | 'you'; away: { text: string; glyph: AwayGlyph } | null; where?: StatusWhere | null }

/** Where they are with you while together ("At your place") or on the phone ("On a call", "Calling you"), the away line while they are asleep, at work or out, else their status. */
export function shown(status: CompanionStatus | null | undefined): { text: string; away: AwayGlyph | null } | null {
  if (!status) return null
  if (status.where?.state === 'together' && status.where.text) return { text: status.where.text, away: togetherGlyph(status.where) }
  if (onThePhone(status.where) && status.where?.text) return { text: status.where.text, away: 'phone' }
  return status.away ? { text: status.away.text, away: status.away.glyph } : status.text ? { text: status.text, away: null } : null
}

/** On a call, or ringing you (companion/life/calls.py). */
/** A weekend visit across the distance (companion/life/long_distance.py) shows luggage, like the chat strip. */
function togetherGlyph(where: StatusWhere): AwayGlyph {
  return where.kind === 'staying' || where.kind === 'hosting' ? 'luggage' : 'pin'
}

export function onThePhone(where: StatusWhere | null | undefined): boolean {
  return where?.kind === 'call' || where?.kind === 'ringing'
}

/** A line as it is read aloud: Retro IM decorations (♫, ~*~, xXx) dropped, and hearts said in words. */
export function spoken(text: string): string {
  return text.replace(/<\/3/g, ' broken heart ').replace(/<3/g, ' love ').replace(/[♫♪]|xXx|[~*]{2,}|~ /g, ' ')
    .replace(/\s+/g, ' ').trim()
}

/** For screen readers: "Maya's status: at work till 6". */
export function statusLabel(name: string, status: CompanionStatus | null | undefined): string {
  const line = shown(status)
  return line ? `${name}'s status: ${spoken(line.text)}` : ''
}

/** The hint under the field while the user edits it. */
export function stickHint(name: string): string {
  return `Stays until something big happens in ${name}'s life. Leave it empty and ${name} picks one.`
}
