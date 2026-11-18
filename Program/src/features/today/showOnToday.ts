import { reducedMotion } from '../../motion'

/** Scrolls to something on Today and marks it for a moment, so the eye lands on it (Iris, 2026-11-18). */
export function showOnToday(id: string) {
  const node = document.getElementById(id)
  if (!node) return
  node.scrollIntoView({ behavior: reducedMotion() ? 'auto' : 'smooth', block: 'center' })
  node.classList.remove('today-found')
  void node.offsetWidth  // Restarts the mark when asked for twice in a row.
  node.classList.add('today-found')
  window.setTimeout(() => node.classList.remove('today-found'), 2400)
}
