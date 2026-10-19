import type { FamilyView } from '../../types'
import { firstName } from './panelText.ts'

export const FAMILY_KEY = ['family']

/** Where "Wants children" came from, under the picker. */
export function wantsHint(view: FamilyView, name: string): string {
  const who = firstName(name)
  if (view.wants_how === 'set') return 'You set this. Pick "Let the app decide" to go back to what fits them.'
  if (view.wants_how === 'description') return `Read from ${who}'s description. Change it any time.`
  if (view.wants_how === 'nudged') return `The app had ${who} at "someday", and ${view.nudged_by ?? 'a baby'} being born in their circle changed that. Change it any time.`
  return `Picked by the app from ${who}'s age and personality. Change it any time.`
}

/** The first choice of each picker: the app's own pick, named. */
export function appPick(label: string): string {
  return `Let the app decide (${label})`
}

/** Where you two stand on starting a family, under the toggle. */
export function decidedHint(view: FamilyView, name: string): string {
  const who = firstName(name)
  if (view.decided_on) return view.decided_how === 'set' ? 'You set it.' : view.decided_how === 'them' ? `${who} brought it up and you said yes.` : `You brought it up and ${who} said yes.`
  if (!view.can_decide) return `This comes after you two decide to live together.`
  if (view.wants === 'no') return `${who} doesn't want children, so they won't bring it up. You still can, in the chat.`
  return `${who} brings it up when the time feels right, and you answer in the chat. You can also set it here.`
}
