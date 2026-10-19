import type { FamilyView, Kid, KidsView } from '../../types'
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

export const KIDS_KEY = ['kids']

/** "Leo, 7, son" or "Ivy, 7 months old, daughter": one of their own children on the Family panel. */
export function kidLine(kid: Kid): string {
  const age = kid.age_text === 'a newborn' ? 'newborn' : kid.age_text
  return `${kid.name}, ${age}, ${kid.relation}`
}

/** Where their kids came from, under the list. */
export function kidsHint(view: KidsView, name: string): string {
  const who = firstName(name)
  if (view.how === 'town') return `${who} had them while living in town, before they were a companion.`
  if (view.how === 'seeded') return `Picked by the app for ${who}. Take a child out of their life if they shouldn't be there.`
  return `Read from ${who}'s description. Take a child out of their life if they shouldn't be there.`
}

/** Under "Where the kids live": who decided it, and the other parent. */
export function whereHint(view: KidsView, name: string): string {
  const who = firstName(name)
  const other = view.other ? ` ${view.other.name}, their other parent, is in ${who}'s circle as their ${view.other.role}.` : ''
  if (view.pattern_how === 'set') return `You set this.${other}`
  if (view.pattern_how === 'fixed') return `Read from ${who}'s description.${other}`
  return `Picked by the app.${other}`
}

/** For a romance: where you stand with their kids. */
export function stepParentLine(view: KidsView, name: string): string | null {
  if (!view.step_parent) return null
  return `You live with ${firstName(name)}, so you're ${view.kids?.length === 1 ? `${view.kids[0].name}'s` : 'their'} step-parent.`
}
