import type { StoryCompanion, StoryMessage, StoryPerson, StoryPlace, StoryScene } from '../../types'

/** "Tuesday, 9:40 AM" from the scene's local time, which is the city's own clock with no offset. */
export function sceneTime(localTime: string): string {
  const [day, clock] = localTime.split('T')
  const [year, month, date] = day.split('-').map(Number)
  const [hour, minute] = clock.split(':').map(Number)
  const weekday = new Date(Date.UTC(year, month - 1, date)).toLocaleDateString('en-US', { weekday: 'long', timeZone: 'UTC' })
  return `${weekday}, ${hour % 12 || 12}:${String(minute).padStart(2, '0')} ${hour < 12 ? 'AM' : 'PM'}`
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

export function whereText(scene: StoryScene): string {
  return `${scene.place.name}, ${scene.place.neighborhood}, ${scene.city.name}`
}

/** "Inside: the back patio, the bar seats" */
export function spotsText(spots: string[]): string {
  return `Inside: ${spots.join(', ')}`
}

/** "Met once · now working as the barista at The Daily Grind" */
export function personLine(person: StoryPerson): string {
  const times = person.meetings === 1 ? 'once' : person.meetings === 2 ? 'twice' : `${person.meetings} times`
  const where = person.place && !person.doing.includes(person.place.name) ? ` at ${person.place.name}` : ''
  return `Met ${times} · now ${person.doing}${where}`
}

/** A story's first open, before anything is said: "Your own story in Baltimore, told by a narrator.", or with a
 * companion "Play out a scene with Mira, anywhere in Baltimore." When their day has them nowhere the story can go,
 * the line says so: "Play out a scene anywhere in Baltimore. Mira isn't out right now." */
export function openingText(scene: { city: { name: string } }, companion?: StoryCompanion): string {
  if (!companion) return `Your own story in ${scene.city.name}, told by a narrator.`
  if (companion.here || companion.place) return `Play out a scene with ${companion.name}, anywhere in ${scene.city.name}.`
  return `Play out a scene anywhere in ${scene.city.name}. ${companion.name} isn't out right now.`
}

/** What the first-open button says and the first line it sends for the user: finding the companion when the story
 * can go to them, else looking around. */
export function openingAction(companion?: StoryCompanion): { label: string; line: string; find: string | null } {
  if (!companion || !(companion.here || companion.place)) return { label: 'Look around', line: 'I look around.', find: null }
  return { label: `Find ${companion.name}`, line: `I look around for ${companion.name}.`, find: companion.here ? null : companion.key }
}

/** "Here with you", "Now at Club Charles" (with the city when it is another one), or "Not out right now". */
export function companionLine(companion: StoryCompanion, city: string): string {
  if (companion.here) return 'Here with you'
  if (!companion.place) return 'Not out right now'
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
