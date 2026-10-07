import { useState } from 'react'

const OPEN_KEY = 'companion:character-helper'

/** Whether the helper is open, as this viewer last left it; open by default while creating a character. */
function readOpen(creating: boolean): boolean {
  try {
    const saved = localStorage.getItem(OPEN_KEY)
    return saved === null ? creating : saved === 'open'
  } catch { return creating }
}

/** The helper's place beside the form: shown only while a text model is connected. */
export function useHelperDock(available: boolean, creating: boolean) {
  const [open, setOpen] = useState(() => readOpen(creating))
  const choose = (value: boolean) => {
    setOpen(value)
    try { localStorage.setItem(OPEN_KEY, value ? 'open' : 'closed') } catch { /* A blocked store only forgets the choice. */ }
  }
  const shown = available && open
  return { shown, offered: available && !open, layout: shown ? 'character-layout with-helper' : 'character-layout', choose }
}
