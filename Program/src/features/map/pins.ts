import type { Pin } from './mapText'

/** Pin glyphs, all one size: the shape carries the meaning (Iris's map spec). Outline paths in a 24px box. */
const HOUSE = '<path d="M4 11.5 12 5l8 6.5V20h-5v-5H9v5H4z"/>'
const CASE = '<rect x="4" y="8" width="16" height="11" rx="2"/><path d="M9 8V6.5A1.5 1.5 0 0 1 10.5 5h3A1.5 1.5 0 0 1 15 6.5V8"/>'
const DOT = '<circle cx="12" cy="12" r="6"/>'

export function pinMarkup(pin: Pin | 'place'): string {
  const shape = pin === 'home' ? HOUSE : pin === 'work' ? CASE : DOT
  return `<svg viewBox="0 0 24 24" aria-hidden="true">${shape}</svg>`
}
