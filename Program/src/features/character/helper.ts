/** The character helper beside the form (docs/character-drafting.md): a pasted character split into fields, and a
 * conversation whose replies propose field changes the user applies or dismisses. Nothing here talks to the server. */
import type { CharacterDefinition } from '../../types'
import { listTexts } from './definition.ts'
import { fieldValue, withField, type DraftField, type FieldValue, type FormState } from './drafting.ts'
import { DAYS, type RoutineBlock } from './schedule.ts'

export type HelperField = DraftField | 'name' | 'location'
export interface HelperReply { reply: string; changes: Partial<Record<HelperField, FieldValue>> }
export interface SplitResult { definition: CharacterDefinition; filled_in: DraftField[]; home_city: string }
export interface CardText { name: string; text: string; truncated: boolean }
export interface HelperTurn { role: 'user' | 'assistant'; content: string }

export type ProposalStatus = 'pending' | 'applied' | 'dismissed'
/** One proposed change: a field, or the whole form from a split character. `previous` is what Undo puts back. */
export type Proposal =
  | { id: string; kind: 'field'; field: HelperField; value: FieldValue; status: ProposalStatus; previous?: FieldValue }
  | { id: string; kind: 'whole'; form: FormState; filledIn: DraftField[]; homeCity: string; status: ProposalStatus; previous?: FormState }
export interface Turn { id: string; message: string; reply: string; proposals: Proposal[] }

export const FIELD_LABELS: Record<HelperField, string> = {
  name: 'Name', location: 'Where they live', identity: 'Who they are', personality: 'Personality', voice: 'Voice', skills: 'Skills',
  flaws: 'Flaws', interests: 'Interests', background: 'Background', appearance: 'Appearance', routine: 'Routine in their words',
  life_themes: 'Life themes', schedule: 'Weekly routine',
}

/** A pasted character this long, on a form that is still mostly empty, is split into every field at once. */
export const SPLIT_LENGTH = 300
const HISTORY_TURNS = 10
const HISTORY_CHARS = 4000

export function isBlank(definition: CharacterDefinition): boolean {
  return !definition.identity.trim() && !definition.personality.trim() && !definition.background.trim()
}

export function wantsSplit(definition: CharacterDefinition, message: string): boolean {
  return isBlank(definition) && message.trim().length >= SPLIT_LENGTH
}

export function blockLine(block: RoutineBlock): string {
  const days = block.days.length === 7 ? 'Every day' : block.days.map((day) => DAYS[day]).join(', ')
  return `${block.label}: ${days}, ${block.start}–${block.end}`
}

/** A field's value as plain text, for comparing before and after. */
export function shownValue(field: HelperField, value: FieldValue): string {
  if (typeof value === 'string') return value
  if (field === 'schedule') return (value as RoutineBlock[]).map(blockLine).join('\n')
  return (value as string[]).join(field === 'skills' || field === 'flaws' ? '\n' : ', ')
}

export function currentValue(state: FormState, field: HelperField): FieldValue {
  return field === 'name' || field === 'location' ? state.definition[field] : fieldValue(state, field)
}

export function withHelperField(state: FormState, field: HelperField, value: FieldValue): FormState {
  if (field === 'name' || field === 'location') return { ...state, definition: { ...state.definition, [field]: value } }
  return withField(state, field, value)
}

/** The form a split character fills: everything from the split, with the user's relationship kept. */
export function splitForm(current: FormState, result: SplitResult): FormState {
  const definition = { ...result.definition, relationship: current.definition.relationship }
  return { definition, texts: listTexts(definition) }
}

/** Proposals for the fields a reply changes, skipping any that already say exactly that. */
export function fieldProposals(state: FormState, changes: HelperReply['changes'], id: () => string): Proposal[] {
  return (Object.entries(changes) as [HelperField, FieldValue][])
    .filter(([field, value]) => field in FIELD_LABELS && shownValue(field, value) !== shownValue(field, currentValue(state, field)))
    .map(([field, value]) => ({ id: id(), kind: 'field', field, value, status: 'pending' }))
}

export function splitReply(result: SplitResult): string {
  const filled = result.filled_in.map((field) => FIELD_LABELS[field].toLowerCase())
  const parts = [`I split ${result.definition.name || 'your character'} into the fields.`]
  if (result.home_city) parts.push(`Your text names ${result.home_city}, so that is their home city.`)
  parts.push(filled.length ? `Your text did not cover ${listed(filled)}, so I filled those in; check them.` : 'Everything came from your text.')
  return parts.join(' ')
}

function listed(items: string[]): string {
  return items.length < 3 ? items.join(' and ') : `${items.slice(0, -1).join(', ')} and ${items.at(-1)}`
}

/** What the server is sent of the conversation so far: the latest turns, each cut to a readable length. */
export function history(turns: Turn[]): HelperTurn[] {
  return turns.slice(-HISTORY_TURNS / 2).flatMap((turn) => [
    { role: 'user' as const, content: turn.message.slice(0, HISTORY_CHARS) },
    { role: 'assistant' as const, content: turn.reply.slice(0, HISTORY_CHARS) },
  ]).filter((turn) => turn.content.trim())
}

/** Apply or undo one proposal; the form value it replaced is kept for Undo. */
export function applied(state: FormState, proposal: Proposal): { state: FormState; proposal: Proposal } {
  if (proposal.kind === 'whole') return { state: proposal.form, proposal: { ...proposal, status: 'applied', previous: state } }
  return { state: withHelperField(state, proposal.field, proposal.value), proposal: { ...proposal, status: 'applied', previous: currentValue(state, proposal.field) } }
}

export function undone(state: FormState, proposal: Proposal): { state: FormState; proposal: Proposal } {
  if (proposal.previous === undefined) return { state, proposal }
  if (proposal.kind === 'whole') return { state: proposal.previous, proposal: { ...proposal, status: 'pending', previous: undefined } }
  return { state: withHelperField(state, proposal.field, proposal.previous), proposal: { ...proposal, status: 'pending', previous: undefined } }
}

/** A file as base64, for the card reader. */
export async function fileData(file: Blob): Promise<string> {
  const bytes = new Uint8Array(await file.arrayBuffer())
  let binary = ''
  for (let index = 0; index < bytes.length; index += 0x8000) binary += String.fromCharCode(...bytes.subarray(index, index + 0x8000))
  return btoa(binary)
}

export const CARD_TYPES = '.json,.png,.txt,.md'
export const isTextFile = (name: string) => /\.(txt|md|markdown)$/i.test(name)
