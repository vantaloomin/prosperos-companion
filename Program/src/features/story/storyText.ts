import type { StoryPlace, StoryScene } from '../../types'

/** "Tuesday, 9:40 am" from the scene's local time, which is the city's own clock with no offset. */
export function sceneTime(localTime: string): string {
  const [day, clock] = localTime.split('T')
  const [year, month, date] = day.split('-').map(Number)
  const [hour, minute] = clock.split(':').map(Number)
  const weekday = new Date(Date.UTC(year, month - 1, date)).toLocaleDateString('en-US', { weekday: 'long', timeZone: 'UTC' })
  return `${weekday}, ${hour % 12 || 12}:${String(minute).padStart(2, '0')} ${hour < 12 ? 'am' : 'pm'}`
}

/** "Nobody you would notice is here.", "The barista is here.", "A regular and a neighbor are here." */
export function aroundText(around: string[]): string {
  if (!around.length) return 'Nobody you would notice is here.'
  const names = around.map((who, index) => index ? who : who[0].toUpperCase() + who.slice(1))
  const list = names.length === 1 ? names[0] : `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`
  return `${list} ${names.length === 1 ? 'is' : 'are'} here.`
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
