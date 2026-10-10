import type { StoryPerson, StoryPlace, StoryScene } from '../../types'

/** "Tuesday, 9:40 am" from the scene's local time, which is the city's own clock with no offset. */
export function sceneTime(localTime: string): string {
  const [day, clock] = localTime.split('T')
  const [year, month, date] = day.split('-').map(Number)
  const [hour, minute] = clock.split(':').map(Number)
  const weekday = new Date(Date.UTC(year, month - 1, date)).toLocaleDateString('en-US', { weekday: 'long', timeZone: 'UTC' })
  return `${weekday}, ${hour % 12 || 12}:${String(minute).padStart(2, '0')} ${hour < 12 ? 'am' : 'pm'}`
}

const COUNTS = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten']

function plural(word: string): string {
  if (/(s|sh|ch|x|z)$/.test(word)) return `${word}es`
  return /[^aeiou]y$/.test(word) ? `${word.slice(0, -1)}ies` : `${word}s`
}

/** Unnamed people who read the same are counted: three of "a local from Canton" are "three locals from Canton". */
export function grouped(around: string[]): string[] {
  const counts = new Map<string, number>()
  for (const who of around) counts.set(who, (counts.get(who) ?? 0) + 1)
  return [...counts.entries()].flatMap(([who, count]) => {
    const unnamed = /^(?:an?|the) (\S+)(.*)$/.exec(who)
    if (count === 1) return [who]
    if (!unnamed) return Array<string>(count).fill(who)
    return [`${COUNTS[count] ?? count} ${plural(unnamed[1])}${unnamed[2]}`]
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

/** "Met once · now working as the barista at The Daily Grind" */
export function personLine(person: StoryPerson): string {
  const times = person.meetings === 1 ? 'once' : person.meetings === 2 ? 'twice' : `${person.meetings} times`
  const where = person.place && !person.doing.includes(person.place.name) ? ` at ${person.place.name}` : ''
  return `Met ${times} · now ${person.doing}${where}`
}
