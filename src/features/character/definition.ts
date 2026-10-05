import type { CharacterDefinition, EmotionalTrait } from '../../types'
import { cleanSchedule } from './schedule.ts'

/** Examples from PRD C6. The user can name any trait; none is enabled by default. */
export const TRAIT_SUGGESTIONS = ['Jealousy', 'Guilt over absence', 'Possessiveness', 'Neediness', 'Tends to sulk', 'Misses you openly']

export const RELATIONSHIPS = [
  { value: 'friendship', label: 'Friendship' },
  { value: 'romance', label: 'Romance' },
  { value: 'mentor', label: 'Mentor' },
  { value: 'family', label: 'Family' },
  { value: 'other', label: 'Something else' },
] as const

export function guessTimezone(): string {
  try { return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC' } catch { return 'UTC' }
}

export function emptyDefinition(timezone = 'UTC'): CharacterDefinition {
  return { name: '', identity: '', personality: '', voice: '', interests: [], background: '', appearance: '', routine: '',
    location: '', home_city: '', relationship: 'friendship', absence_reaction: '', emotional_traits: [], timezone, schedule: [], life_themes: [] }
}

/** Fill fields that older saved versions may lack, so the form always edits a complete definition. */
export function completeDefinition(saved: Partial<CharacterDefinition>): CharacterDefinition {
  return { ...emptyDefinition(), ...saved, interests: saved.interests ?? [], emotional_traits: saved.emotional_traits ?? [], schedule: saved.schedule ?? [], life_themes: saved.life_themes ?? [] }
}

export function parseInterests(text: string): string[] {
  const seen = new Set<string>()
  return text.split(/[,\n]/).map((item) => item.trim()).filter((item) => item && !seen.has(item.toLowerCase()) && seen.add(item.toLowerCase()))
}

/** What is saved: blank trait rows are dropped rather than rejected. */
export function cleanDefinition(definition: CharacterDefinition, interestsText: string, themesText = definition.life_themes.join(', ')): CharacterDefinition {
  const traits: EmotionalTrait[] = definition.emotional_traits.map((trait) => ({ ...trait, name: trait.name.trim(), note: trait.note.trim() })).filter((trait) => trait.name)
  return { ...definition, name: definition.name.trim(), interests: parseInterests(interestsText), emotional_traits: traits,
    schedule: cleanSchedule(definition.schedule), life_themes: parseInterests(themesText) }
}

export function timezones(): string[] {
  try { return Intl.supportedValuesOf('timeZone') } catch { return ['UTC'] }
}
