import { useEffect } from 'react'
import type { CharacterDefinition } from '../../types'
import type { FormState } from '../character/drafting'
import { sidecar } from './store'

/** While a character form is open, the sidecar's character changes land in it, not in a saved version. */
export function useFormBridge(form: FormState, setForm: (form: FormState) => void, definition: () => CharacterDefinition) {
  useEffect(() => { sidecar.setBridge({ form, setForm, definition }) })
  useEffect(() => () => sidecar.setBridge(null), [])
}
