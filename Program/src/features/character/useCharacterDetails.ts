import { useState } from 'react'

const DETAILS_KEY = 'companion:character-details'

/** Whether the character page shows the life details (timezone, texting, routine, week, money, home, wardrobe…).
 * Hidden by default so a new character reads as a person first; the choice is remembered in this browser. */
export function useCharacterDetails(): [boolean, (shown: boolean) => void] {
  const [shown, setShown] = useState(() => {
    try { return localStorage.getItem(DETAILS_KEY) === 'shown' } catch { return false }
  })
  const change = (next: boolean) => {
    setShown(next)
    try { localStorage.setItem(DETAILS_KEY, next ? 'shown' : 'hidden') } catch { /* A blocked store only forgets the choice. */ }
  }
  return [shown, change]
}
