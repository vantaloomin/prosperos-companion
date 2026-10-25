import { useEffect, useState } from 'react'
import { CITIES_CHANNEL, SHOW_CITY_KEY } from '../draft/draftText'
import { reducedMotion } from '../../motion'

/** A city's card in Settings > Cities scrolls into view and lights up for a moment. */
export function jumpToCity(id: string): boolean {
  const card = document.getElementById(`city-${id}`)
  if (!card) return false
  card.scrollIntoView({ behavior: reducedMotion() ? 'auto' : 'smooth', block: 'start' })
  card.focus({ preventScroll: true })
  card.classList.add('jumped')
  window.setTimeout(() => card.classList.remove('jumped'), 2000)
  return true
}

function waiting(): string | null {
  try { return localStorage.getItem(SHOW_CITY_KEY) } catch { return null }
}

/** Show in Companion on the Draft Table: Companion's window turns to Settings > Cities (App.tsx). */
export function useShowCityLink(go: (view: 'settings/life') => void) {
  useEffect(() => {
    if (typeof BroadcastChannel === 'undefined') return
    const channel = new BroadcastChannel(CITIES_CHANNEL)
    channel.addEventListener('message', (event: MessageEvent<unknown>) => {
      if (typeof event.data === 'object' && event.data && 'show' in event.data) go('settings/life')
    })
    return () => channel.close()
  }, [go])
}

/** ...and the saved city's card comes into view once the list has it (features/world/Cities.tsx). */
export function useShowCity(listed: string[] | undefined) {
  const [showing, setShowing] = useState(waiting)
  useEffect(() => {
    if (typeof BroadcastChannel === 'undefined') return
    const channel = new BroadcastChannel(CITIES_CHANNEL)
    channel.addEventListener('message', () => setShowing(waiting()))
    return () => channel.close()
  }, [])
  useEffect(() => {
    if (!showing || !listed?.includes(showing)) return
    const timer = window.setTimeout(() => {
      if (!jumpToCity(showing)) return
      try { localStorage.removeItem(SHOW_CITY_KEY) } catch { /* shown once already */ }
      setShowing(null)
    }, 300)
    return () => window.clearTimeout(timer)
  }, [showing, listed])
}
