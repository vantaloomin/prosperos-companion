/** Personality sliders (companion/world/personality.py): the words the form and the profiles show. */
import type { PersonalityKey, PersonalitySlider, PersonalitySliders, PersonalityTrait } from '../../types'

export const PERSONALITY_KEY = ['personality']

/** The four-letter types "Start from a type" offers: codes only, never a brand name. */
export const TYPES = ['ENFJ', 'ENFP', 'ENTJ', 'ENTP', 'ESFJ', 'ESFP', 'ESTJ', 'ESTP', 'INFJ', 'INFP', 'INTJ', 'INTP', 'ISFJ', 'ISFP', 'ISTJ', 'ISTP']

/** Which slider each of a type's letters sets (E/I outgoing, N/S curious, F/T warm, J/P organized). */
const TYPE_LETTERS: [PersonalityKey, string, string][] = [['social', 'E', 'I'], ['curiosity', 'N', 'S'], ['warmth', 'F', 'T'], ['order', 'J', 'P']]

/** While the app checks a moved slider, the form keeps showing the answer it had (the query's placeholder), so the
 * Personality panel never empties and the slider being moved keeps the keyboard focus. */
export function stillShown<T>(previous: T | undefined): T | undefined {
  return previous
}

/** A stop's words: an end's words, or "In between". */
export function levelLabel(trait: PersonalityTrait, level: number): string {
  return level === 0 ? trait.low : level === 2 ? trait.high : 'In between'
}

/** The summary: the end words of every slider away from the middle; "Even-keeled all round" when none is. */
export function chipsOf(traits: PersonalityTrait[], sliders: PersonalitySliders): string[] {
  const chips = traits.filter((trait) => (sliders[trait.key]?.level ?? 1) !== 1).map((trait) => levelLabel(trait, sliders[trait.key]?.level ?? 1))
  return chips.length ? chips : ['Even-keeled all round']
}

/** The type the sliders read as, when none of its four sliders sits in the middle. */
export function typeOf(sliders: PersonalitySliders): string | null {
  if (TYPE_LETTERS.some(([key]) => (sliders[key]?.level ?? 1) === 1)) return null
  return TYPE_LETTERS.map(([key, high, low]) => sliders[key]?.level === 2 ? high : low).join('')
}

/** Who decided a slider, as its tag says. */
export function sourceLabel(source: PersonalitySlider['source'], idea = 'From your idea'): string {
  return source === 'you' ? 'Set by you' : source === 'idea' ? idea : 'Rolled'
}

/** The user moved a slider: it is theirs now. */
export function moved(sliders: PersonalitySliders, key: PersonalityKey, level: number): PersonalitySliders {
  return { ...sliders, [key]: { level: Math.max(0, Math.min(2, Math.round(level))) as 0 | 1 | 2, source: 'you' } }
}

/** Handing a slider back to the roll: it is left out, and the app rolls it again from the character's seed. */
export function released(sliders: PersonalitySliders, key: PersonalityKey): PersonalitySliders {
  const next = { ...sliders }
  delete next[key]
  return next
}

/** Whether two slider sets say the same, so the form only takes the app's answer when it changes something. */
export function sameSliders(a: PersonalitySliders | null | undefined, b: PersonalitySliders | null | undefined): boolean {
  const keys: PersonalityKey[] = ['social', 'warmth', 'order', 'curiosity', 'stress']
  return keys.every((key) => a?.[key]?.level === b?.[key]?.level && a?.[key]?.source === b?.[key]?.source)
}

/** Whether two slider sets put every slider at the same stop, whoever set it. */
export function sameLevels(a: PersonalitySliders | null | undefined, b: PersonalitySliders | null | undefined): boolean {
  const keys: PersonalityKey[] = ['social', 'warmth', 'order', 'curiosity', 'stress']
  return keys.every((key) => a?.[key]?.level === b?.[key]?.level)
}
