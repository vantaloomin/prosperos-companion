import type { Dating, DatingAim, DatingCard, DatingGender, DatingProfile } from '../../types'

export const DATING_STATUS_KEY = ['dating-status']
export const BLANK: DatingProfile = { name: '', age: 30, gender: 'woman', interested_in: ['man'], looking_for: 'serious', age_min: 25, age_max: 40, bio: '' }

/** Each gender: its value, how the user says it of themself, and how they ask to be shown it. */
export const GENDERS: [DatingGender, string, string][] = [['woman', 'A woman', 'Women'], ['man', 'A man', 'Men'], ['nonbinary', 'Nonbinary', 'Nonbinary people']]
export const AIMS: [DatingAim, string][] = [['serious', 'A relationship'], ['casual', 'Something casual'], ['friends', 'New friends']]

/** "Maya, 29" */
export function cardHeading(card: Pick<DatingCard, 'name' | 'age'>): string {
  return `${card.name}, ${card.age}`
}

/** "Showing women aged 25 to 40, looking for a relationship." */
export function interestText(profile: DatingProfile): string {
  const who = GENDERS.filter(([value]) => profile.interested_in.includes(value)).map(([, , plural]) => plural.toLowerCase())
  const list = who.length > 1 ? `${who.slice(0, -1).join(', ')} and ${who[who.length - 1]}` : who[0]
  const aim = AIMS.find(([value]) => value === profile.looking_for)?.[1].toLowerCase() ?? ''
  return `Showing ${list} aged ${profile.age_min} to ${profile.age_max}, looking for ${aim}.`
}

/** The profile starts as the user's persona (Settings > Worlds), so there is nothing to type unless they want to. */
export function fromPersona(persona: Dating['persona']): DatingProfile {
  if (!persona) return BLANK
  const gender = (['woman', 'man', 'nonbinary'] as const).find((item) => item === persona.gender)
  return { ...BLANK, name: persona.name, age: persona.age && persona.age >= 18 ? persona.age : BLANK.age, bio: persona.about.slice(0, 1000),
    ...(gender ? { gender, interested_in: gender === 'man' ? ['woman'] : ['man'] } : {}) }
}
