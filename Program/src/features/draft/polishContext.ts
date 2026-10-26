import { createContext } from 'react'
import type { Section } from './draftText'

/** Model polish for a list (companion/world/draft/polish.py): what to call, and which list is being polished now. */
export interface Polishing {
  polish: (section: Section) => void
  polishing: Section | null
  /** Whether the user has a text model for Polish; null while that is being found out. */
  ready: boolean | null
  /** The list whose last polish can still be undone (until the next change), and the undo. */
  undoable: Section | null; undo: () => void
  /** Rows Polish changed, until they are edited or the place is saved. */
  polished: ReadonlySet<string>
}
export const PolishContext = createContext<Polishing | null>(null)
