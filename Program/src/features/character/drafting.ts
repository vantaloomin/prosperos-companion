/** The quick start and per-field rewrites, drafted by the configured text model (docs/character-drafting.md). */
import type { CharacterDefinition, Relationship } from '../../types'
import type { ListTexts } from './definition.ts'
import type { RoutineBlock } from './schedule.ts'

export interface DraftRequest { idea: string; name: string; relationship: Relationship; age: string; vibe: string; home_city: string; timezone: string; emotional_edges: boolean
  /** Kept for the drafted sheet; the model drafts the same either way. */
  starting_closeness: number }
export interface DraftResult { definition: CharacterDefinition; career: { id: string; name: string } | null; prompt_version: string }

export type DraftField = 'identity' | 'personality' | 'voice' | 'skills' | 'flaws' | 'interests' | 'background' | 'appearance' | 'routine' | 'life_themes' | 'schedule'
export type FieldValue = string | string[] | RoutineBlock[]
export interface FieldResult { field: DraftField; value: FieldValue }

/** What the form holds: the definition and the list fields it edits as text. */
export interface FormState { definition: CharacterDefinition; texts: ListTexts }

export const AGES = [
  { value: '', label: 'Any adult age' }, { value: 'twenties', label: '20s' }, { value: 'thirties', label: '30s' },
  { value: 'forties', label: '40s' }, { value: 'fifties', label: '50s' }, { value: 'sixty or older', label: '60 or older' },
]

export const VIBES = ['Dry humour', 'Warm and chatty', 'Quiet homebody', 'Outdoorsy', 'Blunt', 'Overthinker', 'Nerdy', 'Easygoing', 'Ambitious', 'Chaotic']

export function emptyRequest(timezone: string): DraftRequest {
  return { idea: '', name: '', relationship: 'friendship', age: '', vibe: '', home_city: '', timezone, emotional_edges: false, starting_closeness: 1 }
}

export function vibeList(vibe: string): string[] {
  return vibe.split(',').map((item) => item.trim()).filter(Boolean)
}

/** A vibe chip adds or removes itself from the free-text vibe, keeping whatever else the user typed. */
export function toggleVibe(vibe: string, pick: string): string {
  const items = vibeList(vibe)
  const has = items.some((item) => item.toLowerCase() === pick.toLowerCase())
  return (has ? items.filter((item) => item.toLowerCase() !== pick.toLowerCase()) : [...items, pick]).join(', ')
}

const LIST_TEXT: Partial<Record<DraftField, { key: keyof ListTexts; separator: string }>> = {
  skills: { key: 'skills', separator: '\n' }, flaws: { key: 'flaws', separator: '\n' },
  interests: { key: 'interests', separator: ', ' }, life_themes: { key: 'themes', separator: ', ' },
}

/** The field as the form shows it, so a rewrite can be undone exactly. */
export function fieldValue(state: FormState, field: DraftField): FieldValue {
  const list = LIST_TEXT[field]
  if (list) return state.texts[list.key]
  return state.definition[field]
}

export function withField(state: FormState, field: DraftField, value: FieldValue): FormState {
  const list = LIST_TEXT[field]
  if (list) return { ...state, texts: { ...state.texts, [list.key]: Array.isArray(value) ? value.join(list.separator) : value } }
  return { ...state, definition: { ...state.definition, [field]: value } }
}
