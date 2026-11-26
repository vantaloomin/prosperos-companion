import type { StoryCompanion, StoryMessage, StoryPerson, StoryPlace, StoryPlan, StoryScene } from '../../types'
import { timeText } from '../today/outingText.ts'

/** The parts of a local time ("2026-11-26T20:06"), which is the city's own clock with no offset. */
function parts(localTime: string): { day: Date; clock: string } {
  const [day, time] = localTime.split('T')
  const [year, month, date] = day.split('-').map(Number)
  const [hour, minute] = time.split(':').map(Number)
  return { day: new Date(Date.UTC(year, month - 1, date)), clock: `${hour % 12 || 12}:${String(minute).padStart(2, '0')} ${hour < 12 ? 'AM' : 'PM'}` }
}

const dayText = (day: Date, options: Intl.DateTimeFormatOptions) => day.toLocaleDateString('en-US', { ...options, timeZone: 'UTC' })

/** "Tuesday, 9:40 AM" from the scene's local time. */
export function sceneTime(localTime: string): string {
  const { day, clock } = parts(localTime)
  return `${dayText(day, { weekday: 'long' })}, ${clock}`
}

/** "Thursday, November 26 · 8:06 PM" under a chapter's number: when its first line was written. */
export function chapterWhen(localTime: string): string {
  const { day, clock } = parts(localTime)
  return `${dayText(day, { weekday: 'long', month: 'long', day: 'numeric' })} · ${clock}`
}

/** "8:06 PM" on a line. On a later day than its chapter began (played past midnight) it says which: "Fri 12:10 AM". */
export function lineTime(localTime: string, began?: string): string {
  const { day, clock } = parts(localTime)
  return began && began.slice(0, 10) !== localTime.slice(0, 10) ? `${dayText(day, { weekday: 'short' })} ${clock}` : clock
}

/** Whether chapters have headings yet: once the story has a second chapter, written or waiting. A book with one
 * chapter needs no number (Iris). */
export function numbered(chapters: { number: number }[], next: unknown): boolean {
  return !!next || chapters.some((chapter) => chapter.number > 1)
}

const COUNTS = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten']

const IRREGULAR: Record<string, string> = { man: 'men', woman: 'women', person: 'people', child: 'children' }
// Words that end the role and start what follows it: "a head chef| at Joe's", "a neighbor| waiting for the bus".
const AFTER_ROLE = /^(.+?)((?: (?:from|at|of|in|on|with|near|by|for|who|that|behind|outside|inside|[a-z]+ing)\b|,).*)?$/

function plural(word: string): string {
  if (IRREGULAR[word]) return IRREGULAR[word]
  if (/(s|sh|ch|x|z)$/.test(word)) return `${word}es`
  return /[^aeiou]y$/.test(word) ? `${word.slice(0, -1)}ies` : `${word}s`
}

/** "head chef at Joe's" -> "head chefs at Joe's": the role's last word, its head noun, takes the plural. */
function pluralRole(phrase: string): string {
  const [, role, rest = ''] = AFTER_ROLE.exec(phrase) ?? [phrase, phrase, '']
  const words = role.split(' ')
  return [...words.slice(0, -1), plural(words[words.length - 1])].join(' ') + rest
}

/** Unnamed people who read the same are counted: three of "a local from Canton" are "three locals from Canton". */
export function grouped(around: string[]): string[] {
  const counts = new Map<string, number>()
  for (const who of around) counts.set(who, (counts.get(who) ?? 0) + 1)
  return [...counts.entries()].flatMap(([who, count]) => {
    const unnamed = /^(?:an?|the) (.+)$/.exec(who)
    if (count === 1) return [who]
    if (!unnamed) return Array<string>(count).fill(who)
    return [`${COUNTS[count] ?? count} ${pluralRole(unnamed[1])}`]
  })
}

/** "Nobody you would notice is here.", "The barista is here.", "A regular and two neighbors are here." */
export function aroundText(around: string[]): string {
  if (!around.length) return 'Nobody you would notice is here.'
  const names = grouped(around).map((who, index) => index ? who : who[0].toUpperCase() + who.slice(1))
  const list = names.length === 1 ? names[0] : `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`
  return `${list} ${around.length === 1 ? 'is' : 'are'} here.`
}

/** The city's places by neighborhood, for the place picker. */
export function placeGroups(places: StoryPlace[]): [string, StoryPlace[]][] {
  const groups = new Map<string, StoryPlace[]>()
  for (const place of places) groups.set(place.neighborhood, [...(groups.get(place.neighborhood) ?? []), place])
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b))
}

/** "Lupa, Fells Point, Baltimore"; "Your home, Canton, Baltimore", or without the neighbourhood where there is none. */
export function whereText(scene: Pick<StoryScene, 'place' | 'city'>): string {
  return [scene.place.name, scene.place.neighborhood, scene.city.name].filter(Boolean).join(', ')
}

/** The user's own home as the place picker's first choice while the story is there, so the picker says where they
 * are; null anywhere else ("Go home" is how to get there). */
export function homeChoice(scene: Pick<StoryScene, 'home'>): { id: string; name: string } | null {
  return scene.home?.here ? { id: scene.home.place_id, name: scene.home.name } : null
}

/** Where "Go home" goes, or null when there is nowhere to go: they are home already, or have no home in this world. */
export function goHome(scene: Pick<StoryScene, 'home'>): { city_id: string; place_id: string } | null {
  return scene.home && !scene.home.here ? { city_id: scene.home.city_id, place_id: scene.home.place_id } : null
}

/** "Inside: the back patio, the bar seats" */
export function spotsText(spots: string[]): string {
  return `Inside: ${spots.join(', ')}`
}

/** "Met once · now working as the barista at The Daily Grind"; "Met 3 times · said yes · now …" once they said yes
 * to the user asking them out. */
export function personLine(person: StoryPerson): string {
  const times = person.meetings === 1 ? 'once' : person.meetings === 2 ? 'twice' : `${person.meetings} times`
  const where = person.place && !person.doing.includes(person.place.name) ? ` at ${person.place.name}` : ''
  return `Met ${times}${person.matched ? ' · said yes' : ''} · now ${person.doing}${where}`
}

/** The plan being played where the story is: "Here with Mira for dinner, until 9:00 PM." */
export function planText(plan: StoryPlan): string {
  return `Here with ${plan.name} for ${plan.what}, until ${timeText(plan.until)}.`
}

/** Whether nothing has been said since the story arrived where it is: the last line is the app's own. */
export function justArrived(messages: Pick<StoryMessage, 'role'>[]): boolean {
  const last = messages[messages.length - 1]
  return !!last && (last.role === 'scene' || last.role === 'cast')
}

/** Where the opening line and its button show, if at all: above an empty story, or under the lines that say who
 * came when a plan is under way here and nothing has been said since. */
export function openingPlace(story: { scene: { plan?: StoryPlan | null }; messages: Pick<StoryMessage, 'role'>[] }): 'top' | 'bottom' | null {
  if (story.scene.plan) return justArrived(story.messages) ? 'bottom' : null
  return story.messages.some((message) => message.role === 'user') ? null : 'top'
}

/** A story's first open, before anything is said: "Your own story in Baltimore, told by a narrator.", or with a
 * companion "Play out a scene with Mira, anywhere in Baltimore." When their day has them nowhere the story can go,
 * the line says so: "Play out a scene anywhere in Baltimore. Mira isn't out right now." With a plan under way
 * (companion/story_plans.py) somewhere else it is the plan: "You and Mira are at Lupa now, for dinner." Where the
 * plan is, the scene's own line already says it, so there is none. */
export function openingText(scene: { city: { name: string }; plan?: StoryPlan | null }, companion?: StoryCompanion): string {
  if (scene.plan) return ''
  if (!companion) return `Your own story in ${scene.city.name}, told by a narrator.`
  if (companion.plan) return `You and ${companion.name} are at ${companion.plan.place} now, for ${companion.plan.what}.`
  if (companion.here || companion.place) return `Play out a scene with ${companion.name}, anywhere in ${scene.city.name}.`
  return `Play out a scene anywhere in ${scene.city.name}. ${companion.name} isn't out right now.`
}

/** What the first-open button says and the first line it sends for the user: finding the companion when the story
 * can go to them, else looking around. With a plan under way it says nothing for the user: "Go to Lupa" only goes
 * there, and "Start the scene" (`begin`) has the narrator open the scene the two are already in. */
export function openingAction(companion?: StoryCompanion, plan?: StoryPlan | null): { label: string; line: string; find: string | null; begin?: boolean } {
  if (plan) return { label: 'Start the scene', line: '', find: null, begin: true }
  if (companion?.plan) return { label: `Go to ${companion.plan.place}`, line: '', find: companion.key }
  if (!companion || !(companion.here || companion.place)) return { label: 'Look around', line: 'I look around.', find: null }
  return { label: `Find ${companion.name}`, line: `I look around for ${companion.name}.`, find: companion.here ? null : companion.key }
}

/** "Here with you", "Now at Club Charles" (with the city when it is another one), or "Not out right now"; with a
 * plan under way, "Here with you for dinner" or "At Lupa for dinner with you". */
export function companionLine(companion: StoryCompanion, city: string): string {
  if (companion.here) return companion.plan ? `Here with you for ${companion.plan.what}` : 'Here with you'
  if (!companion.place) return 'Not out right now'
  if (companion.plan) return `At ${companion.place.name} for ${companion.plan.what} with you`
  return `Now at ${companion.place.name}${companion.city && companion.city !== city ? `, ${companion.city}` : ''}`
}

/** Who is writing while a sent line waits for its replies: the narrator first, then each companion in the scene
 * who has not answered it yet. */
export function writingText(messages: StoryMessage[], clientId: string, companions: { id: string; name: string }[]): string {
  const sent = messages.find((message) => message.client_id === clientId)
  const replies = sent ? messages.filter((message) => message.reply_to === sent.id && message.status === 'complete') : []
  const next = companions.find((companion) => !replies.some((reply) => reply.speaker === companion.id))
  return replies.some((reply) => reply.role === 'narrator') && next ? `${next.name} is answering…` : 'The narrator is writing…'
}
