import { createContext } from 'react'
import type { Section } from './draftText'

/** Model polish for a list (companion/world/draft/polish.py): what to call, and which list is being polished now. */
export const PolishContext = createContext<{ polish: (section: Section) => void; polishing: Section | null } | null>(null)
