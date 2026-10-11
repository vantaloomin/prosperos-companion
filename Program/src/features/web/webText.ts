/** Who knows who (companion/life/web.py): filters and wording, kept apart from the drawing for tests. */

export type WebKind = 'you' | 'companion' | 'circle' | 'acquaintance' | 'townsperson' | 'yours' | 'match'
export type TieKind = 'you' | 'family' | 'partner' | 'work' | 'neighbor' | 'ex' | 'friend' | 'met'
export interface WebNode { id: string; name: string; kind: WebKind; detail: string; hood: string; companion_id?: string; main?: boolean }
export interface WebLink { source: string; target: string; label: string; kind: TieKind }
export interface WebData { nodes: WebNode[]; links: WebLink[] }
export type WebFilter = { kind: 'everyone' } | { kind: 'companions' } | { kind: 'hood'; hood: string } | { kind: 'near'; id: string }

export const KIND_LABELS: Record<WebKind, string> = {
  you: 'You', companion: 'Companion', circle: 'Their circle', acquaintance: 'Met through friends',
  townsperson: 'Around town', yours: 'Your people', match: 'Your match',
}

export const TIE_LABELS: Record<TieKind, string> = {
  you: 'Yours', family: 'Family', partner: 'Partners', work: 'Work', neighbor: 'Neighbours', ex: 'Exes', friend: 'Friends', met: 'Met',
}

/** Everyone within `steps` links of one person, them included. The user knows everyone on the web, so a path
 * through them doesn't count, or every circle would be the whole web. */
export function within(data: WebData, id: string, steps: number): Set<string> {
  const found = new Set([id])
  let edge = [id]
  for (let step = 0; step < steps; step++) {
    const next: string[] = []
    for (const link of data.links) {
      for (const [a, b] of [[link.source, link.target], [link.target, link.source]]) {
        if (edge.includes(a) && !found.has(b) && (a !== 'you' || id === 'you')) { found.add(b); next.push(b) }
      }
    }
    edge = next
  }
  return found
}

/** The part of the web a filter keeps; you and the links between kept people always stay. */
export function filtered(data: WebData, filter: WebFilter): WebData {
  const keep = (node: WebNode): boolean => {
    if (node.kind === 'you') return true
    if (filter.kind === 'companions') return node.kind === 'companion'
    if (filter.kind === 'hood') return node.kind === 'companion' || node.hood === filter.hood
    return true
  }
  let nodes = data.nodes.filter(keep)
  if (filter.kind === 'near') {
    const near = within(data, filter.id, 2)
    nodes = data.nodes.filter((node) => near.has(node.id) || node.kind === 'you')
  }
  const ids = new Set(nodes.map((node) => node.id))
  return { nodes, links: data.links.filter((link) => ids.has(link.source) && ids.has(link.target)) }
}

/** Neighbourhoods anyone lives or works in, for the filter. */
export function hoods(data: WebData): string[] {
  return [...new Set(data.nodes.map((node) => node.hood).filter(Boolean))].sort()
}

/** "Mira's coworker", "your sister": how one person is tied to another, from the first's side. */
export interface Tie { id: string; name: string; label: string; kind: TieKind }
export function tiesOf(data: WebData, id: string): Tie[] {
  const names = new Map(data.nodes.map((node) => [node.id, node.name]))
  return data.links.flatMap((link) => {
    const other = link.source === id ? link.target : link.target === id ? link.source : null
    return other ? [{ id: other, name: names.get(other) ?? '', label: link.label, kind: link.kind }] : []
  }).sort((a, b) => a.name.localeCompare(b.name))
}

/** People whose name matches the search, best first: names starting with it before names containing it. */
export function search(data: WebData, text: string): WebNode[] {
  const query = text.trim().toLowerCase()
  if (!query) return []
  return data.nodes.filter((node) => node.name.toLowerCase().includes(query))
    .sort((a, b) => Number(!a.name.toLowerCase().startsWith(query)) - Number(!b.name.toLowerCase().startsWith(query)) || a.name.localeCompare(b.name))
    .slice(0, 8)
}

/** Bubble sizes: you and companions stand out. */
export function radius(node: WebNode): number {
  return node.kind === 'you' ? 16 : node.kind === 'companion' ? 13 : node.kind === 'circle' ? 9 : 7
}

/** "12 people, 18 ties" */
export function countText(data: WebData): string {
  const people = data.nodes.length - (data.nodes.some((node) => node.kind === 'you') ? 1 : 0)
  return `${people} ${people === 1 ? 'person' : 'people'}, ${data.links.length} ${data.links.length === 1 ? 'tie' : 'ties'}`
}
