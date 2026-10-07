import type { WardrobeCategory, WardrobeItem } from '../../types'

/** Pieces grouped by category in the panel's order, leaving out empty categories. */
export function grouped(items: WardrobeItem[], order: WardrobeCategory[]): [WardrobeCategory, WardrobeItem[]][] {
  return order.map((category): [WardrobeCategory, WardrobeItem[]] => [category, items.filter((item) => item.category === category)])
    .filter(([, pieces]) => pieces.length > 0)
}

/** "Navy scrubs" with a capital, as a list entry. */
export function pieceTitle(item: WardrobeItem): string {
  return item.name.charAt(0).toUpperCase() + item.name.slice(1)
}

/** "Bought on 2026-10-12" for what came later, "Added by you" for the user's own, nothing for the rest. */
export function pieceSince(item: WardrobeItem): string | null {
  if (item.origin === 'generated') return null
  return item.origin === 'user' ? `Added by you on ${item.since}` : `New since ${item.since}`
}

/** "Wearing right now (at work): navy scrubs and cushioned nursing clogs." */
export function wearingText(wearing: { label: string; text: string } | null): string | null {
  if (!wearing || !wearing.text) return null
  return `Wearing right now (${wearing.label}): ${wearing.text}.`
}
