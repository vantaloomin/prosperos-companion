/** Wording for the Kitchen panel (companion/life/kitchen.py). */
import { calendarDay } from '../../when.ts'
import type { KitchenView } from '../../types'

export const KITCHEN_KEY = ['kitchen']

export const DIET_LABELS: Record<string, string> = {
  omnivore: 'Eats everything', pescatarian: 'Pescatarian', vegetarian: 'Vegetarian', vegan: 'Vegan',
}

export const AVOID_LABELS: Record<string, string> = {
  nuts: 'Nuts (allergy)', shellfish: 'Shellfish (allergy)', dairy: 'Dairy', gluten: 'Gluten', pork: 'Pork',
}

/** "Can't really cook", with a capital, for the skill menu. */
export function skillLabel(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1)
}

/** "Made black bean chili" with a capital, or a dash for a day away. */
export function mealLine(day: KitchenView['week'][number]): string {
  if (day.kind === 'away') return 'Away'
  return day.text.charAt(0).toUpperCase() + day.text.slice(1)
}

/** "Tonight", "Tomorrow" or "Mon, Oct 5". */
export function mealDay(day: KitchenView['week'][number], today: string): string {
  if (day.today) return 'Tonight'
  if (day.date > today) return 'Tomorrow'
  return calendarDay(day.date, { weekday: true })
}

/** "Dishes they make a lot: lasagna, shakshuka and pad see ew." or null. */
export function favoritesLine(favorites: string[]): string | null {
  if (!favorites.length) return null
  const list = favorites.length === 1 ? favorites[0] : `${favorites.slice(0, -1).join(', ')} and ${favorites[favorites.length - 1]}`
  return `Dishes they make a lot: ${list}.`
}

/** The favourite dishes box: one per line or comma, empty entries dropped, at most five. */
export function parseFavorites(text: string): string[] {
  return text.split(/[\n,]/).map((item) => item.trim()).filter(Boolean).slice(0, 5)
}

/** Hidden values: "Most nights: cooks 65%, takeout 20%, keeps it simple 15%. Days left: coffee 3, eggs 1." */
export function numbersLine(numbers: KitchenView['numbers']): string | null {
  if (!numbers) return null
  const words: Record<string, string> = { cook: 'cooks', takeout: 'takeout', simple: 'keeps it simple' }
  const rhythm = Object.entries(numbers.rhythm).map(([key, value]) => `${words[key] ?? key} ${value}%`).join(', ')
  const left = Object.entries(numbers.days_left).filter(([, value]) => value !== null).map(([name, value]) => `${name} ${value}`).join(', ')
  return `Most nights: ${rhythm}.${left ? ` Days left: ${left}.` : ''}`
}

/** The realism slider's steps (Settings > Realism > Around the home), shared by the home features: off, light, true to life, dramatic. */
export const KITCHEN_LEVELS = [
  { value: 0, label: 'Off', hint: 'The fridge is always stocked and dinner always works out.' },
  { value: 1, label: 'Light', hint: 'The basics never run out, and a recipe rarely goes wrong.' },
  { value: 2, label: 'True to life', hint: 'Now and then they run out of milk or a recipe goes sideways.' },
  { value: 3, label: 'Dramatic', hint: 'Often out of something, and the odd kitchen disaster ends in takeout.' },
] as const

/** "Their cooking: modern American home cooking." */
export function cuisineLine(cuisine: string): string {
  return `Their cooking: ${cuisine.charAt(0).toLowerCase()}${cuisine.slice(1)}.`
}

/** How many dinner rows show before the older days fold under "Earlier this week". */
export const WEEK_SHOWN = 5
