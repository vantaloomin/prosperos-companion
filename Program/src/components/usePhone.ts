import { useSyncExternalStore } from 'react'

const PHONE = '(max-width: 720px)'

function subscribe(listener: () => void) {
  const query = window.matchMedia(PHONE)
  query.addEventListener('change', listener)
  return () => query.removeEventListener('change', listener)
}

/** Whether the window is phone width (720px or less, as styles.css's phone-only and desktop-only rules). */
export function usePhone(): boolean {
  return useSyncExternalStore(subscribe, () => window.matchMedia(PHONE).matches, () => false)
}
