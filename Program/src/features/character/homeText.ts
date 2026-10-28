import type { HomeItem, HomeKind } from '../../types'
import { calendarDay } from '../../when.ts'

export const KIND_LABELS: Record<HomeKind, string> = { home: 'Home', pet: 'Pet', plant: 'Plant', vehicle: 'Getting around', favorite: 'Favorite thing' }

/** "A one-bedroom in a rowhouse in Fells Point, Baltimore". */
export function homeTitle(item: HomeItem): string {
  // The name heads the card, with the city, and the description is a line under it (itemDetail); a description that
  // only adds to the name ("a studio in a rowhouse in Hampden") heads the card itself.
  const base = (titledByName(item) ? item.name : item.description).replace(/[.\s]+$/, '')
  const text = item.city && !base.includes(item.city) ? `${base}, ${item.city}` : base
  return text.charAt(0).toUpperCase() + text.slice(1)
}

/** "About $1,450 a month (an estimate)", or null where the setting has no rent. */
export function rentText(item: HomeItem): string | null {
  if (item.rent === null || item.rent === undefined) return null
  const amount = `${item.rent_text ?? `${item.currency?.symbol ?? '$'}${item.rent.toLocaleString('en-US')}`} a ${item.rent_period ?? 'month'}`
  if (!item.owned) return `Rent about ${amount} (an estimate)`
  // No mortgage in a medieval kingdom: payments on the place.
  return item.medieval ? `Theirs, paying about ${amount} on it (an estimate)` : `Theirs, with a mortgage of about ${amount} (an estimate)`
}

/** The description when it says more than the name, with what is wrong right now. */
export function itemDetail(item: HomeItem): string {
  const home = item.kind === 'home'
  const description = item.description !== item.name && (!home || titledByName(item)) ? (home ? sentence(item.description.replace(/[.\s]+$/, '')) : item.description) : ''
  const parts = [description, item.out_of_action ? `right now ${item.out_of_action}` : '']
  return parts.filter(Boolean).join('; ')
}

/** "Since 2026-10-12" for things that arrived later, nothing for what they always had. */
export function sinceText(item: HomeItem): string | null {
  if (item.origin === 'generated') return null
  const day = calendarDay(item.since, { year: true })
  return item.origin === 'user' ? `Added by you on ${day}` : `New since ${day}`
}

export function sentence(text: string): string {
  return `${text.charAt(0).toUpperCase()}${text.slice(1)}.`
}

function titledByName(item: HomeItem): boolean {
  return Boolean(item.name) && !item.description.toLowerCase().startsWith(item.name.toLowerCase())
}
