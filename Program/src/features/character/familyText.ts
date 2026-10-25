import type { Custody, FamilyView, Journey, Kid, KidsParent, KidsView, OurChild, OursView } from '../../types'
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
  const kids = view.kids ?? []
  if (kids.length && kids.every((kid) => kid.by_hand)) return `You added ${kids.length === 1 ? 'them' : 'these'}. Edit a child, or take them out of ${who}'s life.`
  if (view.how === 'town') return `${who} had them while living in town, before they were a companion.`
  if (view.how === 'seeded') return `Picked by the app for ${who}. Edit a child, or take them out of their life if they shouldn't be there.`
  return `Read from ${who}'s description. Edit a child, or take them out of their life if they shouldn't be there.`
}

/** Under "Where the kids live": who decided it, and the arrangement spelled out. */
export function whereHint(view: KidsView, name: string): string {
  const who = firstName(name)
  const detail = view.detail ? `: ${view.detail}.` : '.'
  if (view.pattern_how === 'set') return `You set this${detail}`
  if (view.pattern_how === 'fixed') return `Read from ${who}'s description${detail}`
  return `Picked by the app${detail}`
}

/** One choice of "Their other parent": "Mark (ex-husband)". */
export function parentChoice(person: KidsParent): string {
  return `${person.name} (${person.role})`
}

/** Under "Their other parent": who they are to the companion, or that the kids are being raised alone. */
export function otherHint(view: KidsView, name: string): string {
  const who = firstName(name)
  if (!view.other) return `${who} is raising ${(view.kids?.length ?? 0) === 1 ? 'them' : 'the kids'} on their own.`
  const made = view.other.made_up ? ' Picked by the app. Pick "Someone else" to name who it really is.' : ''
  return `${firstName(view.other.name)} is ${who}'s ${view.other.role}.${made}`
}

/** A child's age on the add and edit forms: "Picked for you", "Under a year", "5 years old". */
export function kidAgeChoice(years: number): string {
  if (years < 0) return 'Let the app pick'
  if (years === 0) return 'Under a year'
  return `${years} year${years === 1 ? '' : 's'} old`
}

/** "Where Spock lives" for one child, "Where the kids live" for more. */
export function whereLabel(view: KidsView): string {
  const kids = view.kids ?? []
  return kids.length === 1 ? `Where ${firstName(kids[0].name)} lives` : 'Where the kids live'
}

/** The Undo notice after taking a child out: "Spock is out of Sarek's life." */
export function removedLine(kid: string, name = ''): string {
  return name ? `${kid} is out of ${firstName(name)}'s life.` : `${kid} is out of their life.`
}

/** Over the "Someone else" form when the app made up the other parent: they become who the user names. */
export function madeUpLine(other: string): string {
  const who = firstName(other)
  return `The app made up ${who}. ${who} becomes the person you name here.`
}

/** Son, daughter or child, as the forms offer them, by pronouns. */
export const KID_RELATIONS = [{ pronouns: 'he/him', label: 'Son' }, { pronouns: 'she/her', label: 'Daughter' }, { pronouns: 'they/them', label: 'Child' }] as const

/** The add form (`kid` undefined) or a child's edit form: what it starts with, says and sends to. */
export function kidForm(kid: Kid | undefined) {
  if (!kid) {
    return { adding: true, prefix: 'kid-add', title: 'Add a child', submit: 'Add', placeholder: 'Let the app pick', name: '', pronouns: '', age: -1,
      youngest: -1, path: '/life/steps/kids', method: 'POST' }
  }
  return { adding: false, prefix: `kid-${kid.id}`, title: `Edit ${kid.name}`, submit: 'Save', placeholder: undefined, name: kid.name,
    pronouns: kid.pronouns, age: Math.min(kid.age, MAX_KID_AGE), youngest: 0, path: `/life/steps/kids/${kid.id}`, method: 'PATCH' }
}

/** What the add or edit form sends: only what the user filled in or changed (the app picks or keeps the rest). */
export function kidChange(kid: Kid | undefined, name: string, pronouns: string, age: number): { name?: string; age?: number; pronouns?: string } {
  const change: { name?: string; age?: number; pronouns?: string } = {}
  if (name.trim() && name.trim() !== kid?.name) change.name = name.trim()
  if (pronouns && pronouns !== kid?.pronouns) change.pronouns = pronouns
  if (age >= 0 && age !== kid?.age) change.age = age
  return change
}

/** "Saved." after an edit; "Added Spock." after adding (the newest child, when the app picked the name). */
export function kidSaved(kid: Kid | undefined, view: KidsView): string {
  if (kid) return 'Saved.'
  const added = [...(view.kids ?? [])].filter((item) => item.by_hand).pop()
  return added ? `Added ${added.name}.` : 'Added.'
}

/** The oldest a child of theirs can be (a grown son or daughter goes in their circle). */
export const MAX_KID_AGE = 17

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

/** Under "Where they live": since when, who picked it, and the arrangement spelled out. */
export function custodyHint(custody: Custody, name: string): string {
  const who = firstName(name)
  if (!custody.split) return `You live in ${custody.city ?? 'another city'} now, so they stay with ${who} and you see them when you visit.`
  const how = custody.how === 'set' ? 'You set this' : `Picked by the app since you and ${who} split up`
  const far = custody.far ? ` You live in ${custody.city ?? 'another city'} now, so a week each can't work.` : ''
  return `${how}: ${custody.detail}.${far}`
}

/** In place of "A family together" while you two are split up. */
export function splitLine(custody: Custody, name: string): string {
  const when = custody.ended_on ? ` on ${stepDate(custody.ended_on)}` : ''
  return `You and ${firstName(name)} split up${when}; this comes back if you get back together.`
}

/** Under "Another child": where it stands. */
export function anotherHint(view: FamilyView, name: string): string {
  const who = firstName(name)
  if (view.another_on) return `You two decided on ${stepDate(view.another_on)}.`
  if (view.can_decide_another) return `${who} may bring it up when the time feels right, and you answer in the chat. You can also set it here.`
  return 'This can come up a year and a half after your first child came home, and only once.'
}

/** The summary of each "Why it went this way" under a journey (Hidden values), so two or three in a row say which is
 * which: how soon, the hard turn, the wait, who the child is, whether fostering leads to adopting. */
export function outcomeSummary(key: string, route: string): string {
  const pregnancy = PREGNANCY.includes(route)
  const summaries: Record<string, string> = {
    soon: route === 'surrogacy' ? 'Why the surrogacy took this long' : 'Why finding out took this long',
    turn: pregnancy ? 'Why the pregnancy went this way' : 'Why it went this way',
    wait: 'Why the wait for a match is this long',
    match: 'How old the child will be',
    fostered: 'Whether fostering leads to adopting',
  }
  return summaries[key] ?? 'Why it went this way'
}
