import type { ArgumentSource, ContextCategory, ContextMapping, ContextPurpose, ContextTool, MappingSuggestion, Observation, ToolArgument } from '../../types'

export const CONTEXT_KEY = ['context-tools']
export const CATEGORY_ORDER: ContextCategory[] = ['weather', 'news', 'local_events', 'web_search', 'link']
export const CATEGORY_LABELS: Record<ContextCategory, string> = { weather: 'Weather', news: 'News and recent events', local_events: 'Local events', link: 'Reading links', web_search: 'Web search' }
export const SOURCE_LABELS: Record<ArgumentSource, string> = {
  place: 'Your city or region', latitude: 'Latitude', longitude: 'Longitude', topic: 'Topic you asked about', date: "Today's date", literal: 'A fixed value', url: 'The link you pasted',
}

export interface ServiceDraft { name: string; transport: 'stdio' | 'http'; program: string; args: string; url: string; secret: string; secretName: string }

/** The request body for a service: the program and one argument per line, or the address. */
export function serviceBody(draft: ServiceDraft): Record<string, unknown> {
  const base = { name: draft.name.trim(), transport: draft.transport, secret: draft.secret || undefined, secret_name: draft.secretName.trim() }
  if (draft.transport === 'http') return { ...base, url: draft.url.trim() }
  const args = draft.args.split('\n').map((line) => line.trim()).filter(Boolean)
  return { ...base, command: [draft.program.trim(), ...args] }
}

/** Hosted search services that work without a key; each is added and checked, and stays off until approved. */
export const SEARCH_PRESETS = [
  { id: 'parallel', name: 'Parallel Search', url: 'https://search.parallel.ai/mcp', note: 'Web search and page reading; free without a key, at lower limits.' },
  { id: 'exa', name: 'Exa', url: 'https://mcp.exa.ai/mcp', note: 'Web search and page reading; free without a key, rate-limited.' },
  { id: 'firecrawl', name: 'Firecrawl', url: 'https://mcp.firecrawl.dev/v2/mcp', note: 'Search and page scraping; a small free allowance without a key.' },
] as const

/** The label for when a mapping runs, in the editor. */
export function purposeLabel(category: ContextCategory, purpose: ContextPurpose, name: string): string {
  if (category === 'link') return 'When a link you paste cannot be read on this computer'
  if (category === 'web_search') return 'When you ask in chat to search or look something up'
  return purpose === 'conversation' ? 'When you ask about it in chat' : `For ${name}'s city, when it is a real place`
}

/** Categories with a "try it" button: those that look up a place, not a link or a search. */
export function canTry(category: ContextCategory): boolean {
  return category !== 'link' && category !== 'web_search'
}

export interface MappingDraft { tool: string; arguments: Record<string, ToolArgument>; run_in: ContextPurpose[] }

/** Start from the saved mapping, else the app's suggestion, else the first tool with nothing mapped. */
export function initialMapping(tools: ContextTool[], saved?: ContextMapping, suggestion?: MappingSuggestion): MappingDraft {
  if (saved) return { tool: saved.tool, arguments: saved.arguments, run_in: saved.run_in }
  if (suggestion) return { tool: suggestion.tool, arguments: suggestion.arguments, run_in: ['conversation'] }
  return { tool: tools[0]?.name ?? '', arguments: {}, run_in: ['conversation'] }
}

/** Sources a category may send: only news, events and search send a topic, and only link reading sends the link. */
export function sourcesFor(category: ContextCategory): ArgumentSource[] {
  if (category === 'link') return ['url', 'literal']
  if (category === 'web_search') return ['topic', 'literal']
  const all: ArgumentSource[] = ['place', 'latitude', 'longitude', 'topic', 'date', 'literal']
  return category === 'weather' ? all.filter((source) => source !== 'topic') : all
}

/** Required properties of the chosen tool that the draft does not fill yet. */
export function missingArguments(tool: ContextTool | undefined, args: Record<string, ToolArgument>): string[] {
  return (tool?.input_schema.required ?? []).filter((name) => !args[name] || (args[name].source === 'literal' && (args[name].value ?? '') === ''))
}

function lookupTitle(item: Observation): string {
  if (item.category === 'link') return `Link: ${String(item.location?.url ?? item.arguments.url ?? '')}`
  const where = item.location?.label ? ` for ${item.location.label}` : ''
  const whose = item.location?.whose === 'companion' ? " (the companion's city)" : ''
  return `${CATEGORY_LABELS[item.category]}${where}${whose}`
}

function lookupState(item: Observation, now: Date): { state: string; tone: 'ok' | 'stale' | 'failed' } {
  if (item.status === 'refused') return { state: `Not looked up: ${item.error ?? 'a limit applied'}`, tone: 'failed' }
  if (item.status === 'failed') return { state: `Failed: ${item.error ?? 'no result'}`, tone: 'failed' }
  if (item.fresh_until !== null && new Date(item.fresh_until) > now) return { state: `Current until ${clock(item.fresh_until)}`, tone: 'ok' }
  return { state: 'Out of date; no longer used as current', tone: 'stale' }
}

/** The draft with one property sent from `source`, or not sent at all. */
export function withSource(draft: MappingDraft, property: string, source: ArgumentSource | ''): MappingDraft {
  const next = { ...draft.arguments }
  if (source === '') delete next[property]
  else next[property] = source === 'literal' ? { source, value: '' } : { source }
  return { ...draft, arguments: next }
}

export function withPurpose(draft: MappingDraft, purpose: ContextPurpose, on: boolean): MappingDraft {
  return { ...draft, run_in: on ? [...new Set([...draft.run_in, purpose])] : draft.run_in.filter((item) => item !== purpose) }
}

/** A draft can be saved once it names a tool, fills its required arguments and runs somewhere. */
export function canSave(draft: MappingDraft, tool: ContextTool | undefined): boolean {
  return Boolean(draft.tool) && draft.run_in.length > 0 && missingArguments(tool, draft.arguments).length === 0
}

/** A plain account of one lookup: what, for where, from whom, and whether it counts as current. */
export function observationSummary(item: Observation, now: Date = new Date()): { title: string; state: string; tone: 'ok' | 'stale' | 'failed' } {
  return { title: lookupTitle(item), ...lookupState(item, now) }
}

/** What was sent, as "name: value" pairs. */
export function sentArguments(item: Observation): string {
  const pairs = Object.entries(item.arguments).map(([name, value]) => `${name}: ${String(value)}`)
  return pairs.length ? pairs.join(', ') : 'nothing'
}

function clock(value: string): string {
  return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
