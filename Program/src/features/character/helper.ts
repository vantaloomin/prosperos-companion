/** A pasted character split into the form's fields, and the character fields the sidecar may change
 * (docs/character-drafting.md, docs/sidecar.md). Nothing here talks to the server. */
import type { CharacterDefinition } from '../../types'
import { listTexts } from './definition.ts'
import { fieldValue, withField, type DraftField, type FieldValue, type FormState } from './drafting.ts'
import { DAYS, type RoutineBlock } from './schedule.ts'

export type HelperField = DraftField | 'name' | 'location' | 'seen_as' | 'sees_self'
const PLAIN: HelperField[] = ['name', 'location', 'seen_as', 'sees_self']
export interface SplitResult { definition: CharacterDefinition; filled_in: DraftField[]; home_city: string }
export interface CardText { name: string; text: string; truncated: boolean }

export const FIELD_LABELS: Record<HelperField, string> = {
  name: 'Name', location: 'Where they live', identity: 'Who they are', personality: 'Personality', voice: 'Voice', skills: 'Skills',
  flaws: 'Flaws', interests: 'Interests', background: 'Background', appearance: 'Appearance', routine: 'Routine in their words',
  life_themes: 'Life themes', schedule: 'Weekly routine', seen_as: 'How others see them', sees_self: 'How they see themselves',
}

/** A pasted character this long, on a form that is still mostly empty, is split into every field at once. */
export const SPLIT_LENGTH = 300

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
  return isPlain(field) ? state.definition[field] ?? '' : fieldValue(state, field)
}

export function withHelperField(state: FormState, field: HelperField, value: FieldValue): FormState {
  if (isPlain(field)) return { ...state, definition: { ...state.definition, [field]: value } }
  return withField(state, field, value)
}

function isPlain(field: HelperField): field is 'name' | 'location' | 'seen_as' | 'sees_self' {
  return PLAIN.includes(field)
}

/** The form a split character fills: everything from the split, with the user's relationship kept. */
export function splitForm(current: FormState, result: SplitResult): FormState {
  const definition = { ...result.definition, relationship: current.definition.relationship }
  return { definition, texts: listTexts(definition) }
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

/** A file as base64, for the card reader. */
export async function fileData(file: Blob): Promise<string> {
  const bytes = new Uint8Array(await file.arrayBuffer())
  let binary = ''
  for (let index = 0; index < bytes.length; index += 0x8000) binary += String.fromCharCode(...bytes.subarray(index, index + 0x8000))
  return btoa(binary)
}

export const CARD_TYPES = '.json,.png,.txt,.md'
export const isTextFile = (name: string) => /\.(txt|md|markdown)$/i.test(name)
