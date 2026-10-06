import type { HomeItem, HomeKind } from '../../types'

export const KIND_LABELS: Record<HomeKind, string> = { home: 'Home', pet: 'Pet', plant: 'Plant', vehicle: 'Getting around', favorite: 'Favourite thing' }

/** "A one-bedroom in a rowhouse in Fells Point, Baltimore". */
export function homeTitle(item: HomeItem): string {
  const text = item.city && !item.description.includes(item.city) ? `${item.description}, ${item.city}` : item.description
  return text.charAt(0).toUpperCase() + text.slice(1)
}

/** "About $1,450 a month (an estimate)", or null where the setting has no rent. */
export function rentText(item: HomeItem): string | null {
  if (item.rent === null || item.rent === undefined) return null
  return `Rent about ${item.currency?.symbol ?? '$'}${item.rent.toLocaleString('en-US')} a ${item.rent_period ?? 'month'} (an estimate)`
}

/** The description when it says more than the name, with what is wrong right now. */
export function itemDetail(item: HomeItem): string {
  const parts = [item.description !== item.name ? item.description : '', item.out_of_action ? `right now ${item.out_of_action}` : '']
  return parts.filter(Boolean).join('; ')
}

/** "Since 2026-10-12" for things that arrived later, nothing for what they always had. */
export function sinceText(item: HomeItem): string | null {
  if (item.origin === 'generated') return null
  return item.origin === 'user' ? `Added by you on ${item.since}` : `New since ${item.since}`
}

export function sentence(text: string): string {
  return `${text.charAt(0).toUpperCase()}${text.slice(1)}.`
}
