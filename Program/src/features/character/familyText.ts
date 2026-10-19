import type { FamilyView, Journey, Kid, KidsView, OurChild, OursView } from '../../types'
import { firstName } from './panelText.ts'
import { stepDate } from './stepsText.ts'

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

/** Where you two stand on starting a family, under the toggle; once a child is on the way, why it is locked. */
export function decidedHint(view: FamilyView, name: string): string {
  const hint = standing(view, name)
  return view.journey && view.journey.status !== 'planned' ? `${hint} ${lockedLine(view.journey)}` : hint
}

function standing(view: FamilyView, name: string): string {
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

/** Under "Where the kids live": who decided it, the arrangement spelled out, and the other parent. */
export function whereHint(view: KidsView, name: string): string {
  const who = firstName(name)
  const other = view.other ? ` ${firstName(view.other.name)}, their other parent, is in ${who}'s circle as their ${view.other.role}.` : ''
  const detail = view.detail ? `: ${view.detail}.` : '.'
  if (view.pattern_how === 'set') return `You set this${detail}${other}`
  if (view.pattern_how === 'fixed') return `Read from ${who}'s description${detail}${other}`
  return `Picked by the app${detail}${other}`
}

/** The first choice of "Where the kids live": the description's arrangement or the app's pick, named. */
export function wherePick(view: KidsView, name: string, label: string): string {
  if (view.pattern_how === 'fixed') return `From ${firstName(name)}'s description (${label})`
  return appPick(view.pattern_how === 'set' ? 'what fits them' : label)
}

/** "Leo", "Leo and Mia", "Leo, Mia and Sam". */
export function kidNames(view: KidsView): string {
  const names = (view.kids ?? []).map((kid) => kid.name)
  return names.length < 2 ? names.join('') : `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`
}

/** For a romance: where you stand with their kids, as a labelled line under them. */
export function standingLine(view: KidsView, name: string): { label: string; text: string } | null {
  const who = firstName(name)
  const them = (view.kids?.length ?? 0) === 1 ? kidNames(view) : 'them'
  if (view.step_parent) return { label: 'Step-parent', text: `you live with ${who}, so you're ${kidNames(view)}'s step-parent.` }
  if (view.meeting === 'unmet') return { label: 'Not met yet', text: `${who} will bring it up when the time feels right.` }
  if (view.meeting === 'soon') return { label: 'Meeting soon', text: `you'll meet ${them} at the get-together ${who} planned.` }
  if (view.meeting === 'met') return { label: 'Met', text: `you've met ${them}.` }
  return null
}

const PREGNANCY = ['expecting_them', 'expecting_you', 'surrogacy']

function lockedLine(journey: Journey): string {
  if (journey.status === 'home') return `Locked now that ${journey.name ?? 'your child'} is home.`
  return `Locked while ${PREGNANCY.includes(journey.route) ? 'a baby' : 'a child'} is on the way.`
}

/** Under the route once a child is on the way: why the picker is gone. */
export function routeHint(journey: Journey): string {
  if (journey.status === 'home') return 'Set when you started.'
  return `Set when you started; it can't change while ${PREGNANCY.includes(journey.route) ? 'a baby' : 'a child'} is on the way.`
}

/** Where the journey stands, in a line: "Expecting, due in June", "Waiting for a match", "Ivy came home Mar 3, 2028". */
export function journeyLine(journey: Journey, name: string, day: (value: string) => string): string {
  const who = firstName(name)
  if (journey.status === 'home' && journey.arrived_on) {
    return `${journey.name ?? 'Your child'} ${PREGNANCY.includes(journey.route) ? 'was born' : 'came home'} ${day(journey.arrived_on)}`
  }
  if (journey.due_on) {
    const month = new Date(`${journey.due_on}T12:00:00`).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
    return `Expecting a baby, due in ${month}`
  }
  if (journey.status === 'planned') return `${who} and you have decided. Nothing has happened yet.`
  return waitingLine(journey, new Set(journey.stages.filter((item) => item.done).map((item) => item.key)))
}

function waitingLine(journey: Journey, reached: Set<string>): string {
  if (journey.route === 'fostering') return reached.has('home') ? `${journey.name} lives with you two` : 'Becoming foster parents'
  if (journey.route === 'adoption') return reached.has('match') ? `Matched with ${journey.name}` : 'Adopting: waiting for a match'
  if (journey.route === 'surrogacy') return 'Having a baby through a surrogate'
  return journey.name ? `Taking in ${journey.name}` : 'Waiting'
}

/** Under the child's name: who picked it. */
export function nameHint(journey: Journey, name: string): string {
  if (journey.renamed) return 'You named them. It stays as you set it.'
  return `${firstName(name)} suggested it. Rename them any time; moments that already happened keep the name they had.`
}

export const OURS_KEY = ['ours']

/** "Mia, 2, daughter" or "Ivy, newborn, daughter": one of your children with them, on its card. */
export function ourChildLine(child: OurChild): string {
  return `${child.name}, ${ourChildAge(child.age_text)}, ${child.relation}`
}

/** 'newborn', '3 weeks old', '7 months old', '1 year old', '6 years old'. */
export function ourChildAge(ageText: string): string {
  if (ageText === 'a newborn') return 'newborn'
  if (!/^\d+$/.test(ageText)) return ageText
  return `${ageText} year${ageText === '1' ? '' : 's'} old`
}

/** "Easygoing and quick to laugh. Lately into puddles." The sheet in a sentence or two. */
export function sheetText(child: OurChild): string {
  const temperament = child.temperament ? `${child.temperament[0].toUpperCase()}${child.temperament.slice(1)}.` : ''
  return [temperament, child.likes ? `Lately into ${child.likes}.` : ''].filter(Boolean).join(' ')
}

/** "Born Mar 3, 2028" or "Came home Mar 3, 2028": the collapsed line over how it went. */
export function arrivalText(child: OurChild, route: string | undefined, day: (value: string) => string): string {
  const born = !route || PREGNANCY.includes(route)
  return `${born ? 'Born' : 'Came home'} ${day(born ? child.born_on : child.arrived_on)}`
}

/** Under "Who looks after them": who picked it and when it applies. */
const CARE_HINTS: Record<string, string> = {
  both_work: 'you both keep working while they are looked after in the day',
  part_time: '{name} works part-time',
  them_home: '{name} stays home with them',
  you_home: 'you stay home with them',
}

export function careHint(view: OursView, name: string): string {
  const who = firstName(name)
  const how = view.care_how === 'set' ? 'You set this' : `Picked by the app from ${who}'s work and your money`
  if (!view.care_now) return `${how}. Once the youngest is at school you both work again; this comes back with a new baby.`
  return `${how}: ${CARE_HINTS[view.care ?? ''] ?? 'this lasts'} until the youngest starts school.`.replace('{name}', who)
}

/** Under "Another child": where it stands. */
export function anotherHint(view: FamilyView, name: string): string {
  const who = firstName(name)
  if (view.another_on) return `You two decided on ${stepDate(view.another_on)}.`
  if (view.can_decide_another) return `${who} may bring it up when the time feels right, and you answer in the chat. You can also set it here.`
  return 'This can come up a year and a half after your first child came home, and only once.'
}
