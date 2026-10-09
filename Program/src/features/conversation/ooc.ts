/**
 * Out-of-character messages go to the helper (Feature Hit List #6). Before a message is sent, the composer looks
 * for the user's out-of-character markers: a starting word (OOC:) or an opening and closing pair ((( and ))). What
 * they mark goes to the helper (the sidecar) instead of the companion, and never into the chat; the rest goes to
 * the companion as usual. Settings > General > Out-of-character messages changes the markers or turns it off.
 */
export interface OocMarker { open: string; close: string }

export const DEFAULT_OOC_MARKERS: OocMarker[] = [{ open: 'OOC:', close: '' }, { open: '((', close: '))' }]

export interface OocSplit { story: string; aside: string }

/** The message split into what goes to the companion (`story`) and what goes to the helper (`aside`). */
export function splitOoc(text: string, markers: OocMarker[]): OocSplit {
  const start = markers.find((marker) => !marker.close && text.trimStart().toLowerCase().startsWith(marker.open.toLowerCase()))
  if (start) return { story: '', aside: text.trimStart().slice(start.open.length).trim() }
  const pairs = markers.filter((marker) => marker.close)
  const story: string[] = []
  const asides: string[] = []
  let rest = text
  for (let found = firstPair(rest, pairs); found; found = firstPair(rest, pairs)) {
    story.push(rest.slice(0, found.at))
    const inside = rest.slice(found.at + found.marker.open.length)
    const end = inside.indexOf(found.marker.close)
    asides.push((end < 0 ? inside : inside.slice(0, end)).trim())
    rest = end < 0 ? '' : inside.slice(end + found.marker.close.length)
  }
  if (!asides.length) return { story: text, aside: '' }
  story.push(rest)
  return { story: tidy(story.join(' ')), aside: asides.filter(Boolean).join('\n') }
}

function firstPair(text: string, pairs: OocMarker[]): { at: number; marker: OocMarker } | null {
  let best: { at: number; marker: OocMarker } | null = null
  for (const marker of pairs) {
    const at = text.indexOf(marker.open)
    if (at >= 0 && (!best || at < best.at)) best = { at, marker }
  }
  return best
}

/** Spaces left where an aside was taken out, without touching the user's line breaks. */
function tidy(text: string): string {
  return text.replace(/[ \t]{2,}/g, ' ').replace(/ +([.,!?;:])/g, '$1').replace(/[ \t]+\n/g, '\n').trim()
}
