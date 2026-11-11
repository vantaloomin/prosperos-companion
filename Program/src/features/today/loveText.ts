import type { CircleLove } from '../../types'

/** Their love life in Edit person (companion/life/love_pick.py): the user's pick, '' while it is the app's. */
export type LovePick = '' | 'single' | 'seeing' | 'engaged' | 'married'
export interface LoveValues { love: LovePick; partner: string }

export const LOVE_CHOICES: { value: Exclude<LovePick, ''>; label: string }[] = [
  { value: 'single', label: 'Single' }, { value: 'seeing', label: 'Seeing someone' },
  { value: 'engaged', label: 'Engaged' }, { value: 'married', label: 'Married' },
]

/** On the label, not under the field (Iris, relationship control direction (d)). */
export const LOVE_TIP = 'Left to the app, their love life follows the world: they may meet someone, marry or split up. Your pick holds until you set it back to the app.'

/** States with someone to name in "Who with". */
export const withPartner = (love: LovePick) => love === 'seeing' || love === 'engaged' || love === 'married'

const APP_WORDS: Record<CircleLove['state'], [string, string]> = {
  single: ['Single', 'Single'], seeing: ['Seeing someone', 'Seeing {p}'], engaged: ['Engaged', 'Engaged to {p}'],
  married: ['Married', 'Married to {p}'], separated: ['Separated', 'Separated from {p}'], divorced: ['Divorced', 'Divorced'],
  widowed: ['Widowed', 'Widowed'],
}

/** "Let the app pick (Seeing Liss)": what the app has now, by first name, while it is the app's (Iris addition 2). */
export function appLove(info?: CircleLove): string {
  if (!info || info.set) return 'Let the app pick'
  const [plain, named] = APP_WORDS[info.state]
  return `Let the app pick (${info.partner ? named.replace('{p}', info.partner) : plain})`
}

/** The form's values: the user's pick when there is one, else the app's. */
export function loveValues(info?: CircleLove): LoveValues {
  if (!info?.set) return { love: '', partner: '' }
  const love = LOVE_CHOICES.some((choice) => choice.value === info.state) ? info.state as LovePick : ''
  return { love, partner: withPartner(love) ? info.partner ?? '' : '' }
}

/** What the server is sent: nothing when unchanged; '' hands it back to the app. "Who with" counts only when it is
 * on (Iris (c)): Single or the app's pick send no name. */
export function loveChange(before: LoveValues, after: LoveValues): Record<string, string> {
  const partner = withPartner(after.love) ? after.partner.trim() : ''
  const was = withPartner(before.love) ? before.partner.trim() : ''
  if (after.love === before.love && partner === was) return {}
  return partner ? { love: after.love, partner_name: partner } : { love: after.love }
}

/** "Who with": the other people in the circle, and where each stands now in muted words (Iris addition 1). */
export function loveSuggestions(info?: CircleLove): { options: string[]; notes: Record<string, string> } {
  const people = info?.people ?? []
  return { options: people.map((person) => person.name), notes: Object.fromEntries(people.filter((person) => person.stands).map((person) => [person.name, person.stands as string])) }
}
