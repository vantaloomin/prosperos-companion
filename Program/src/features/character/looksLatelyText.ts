/** Looks that change (companion/life/grooming.py): the Realism slider's words and the Character page's lines. */

export const LOOKS_KEY = ['grooming']

/** Settings > Realism > Their days, from never (0) to often (3); the presets set it too (presetChoices.ts). */
export const LOOKS_LEVELS = [
  { label: 'Never', hint: 'Everyone keeps the look they have now. Changes already made are set aside until you turn this back on.' },
  { label: 'Now and then', hint: 'Haircuts, nails and a summer tan, and only now and then something new: a cut, a soft color or new glasses.' },
  { label: 'Like real life', hint: 'Hair grows and gets cut, nails get done, a tan comes and fades, and every few months they try something bold.' },
  { label: 'Often', hint: 'They change it up more often: bright colors, big cuts, new glasses, a beard grown or shaved off.' },
]

const FIELD_NAMES: Record<string, string> = { hair: 'hair', facial_hair: 'facial hair', skin: 'skin', feature: 'what people notice about them', nails: 'nails' }

/** "Staying as you wrote them: hair and nails." for looks the user wrote, or null when every look is the app's. */
export function fixedLine(fields: string[]): string | null {
  const names = fields.map((field) => FIELD_NAMES[field] ?? field)
  if (!names.length) return null
  const listed = names.length === 1 ? names[0] : `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`
  return `Staying exactly as you wrote ${names.length === 1 ? 'it' : 'them'}: ${listed}.`
}

/** "Dyed her hair copper red." */
export function changeLine(text: string): string {
  return `${text.charAt(0).toUpperCase()}${text.slice(1)}.`
}
