import { useState } from 'react'
import { Sparkles } from 'lucide-react'
import { api } from '../../api'
import type { CharacterDefinition } from '../../types'
import type { DraftField, FieldResult, FieldValue } from './drafting'

interface Props { field: DraftField; label: string; definition: () => CharacterDefinition; current: FieldValue; apply: (value: FieldValue) => void }

/** Ask the text model to rewrite one field in keeping with the rest; the old text can be put back. */
export function FieldHelp({ field, label, definition, current, apply }: Props) {
  const [open, setOpen] = useState(false)
  const [request, setRequest] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [previous, setPrevious] = useState<FieldValue | null>(null)

  const rewrite = async () => {
    setBusy(true)
    setError('')
    try {
      const result = await api<FieldResult>('/companion/draft/field', { definition: definition(), field, request })
      setPrevious(current)
      apply(result.value)
      setOpen(false)
      setRequest('')
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'The rewrite did not work.')
    } finally { setBusy(false) }
  }
  const undo = () => { if (previous !== null) apply(previous); setPrevious(null) }

  if (!open) {
    return (
      <div className="field-help">
        <button type="button" className="text-button" onClick={() => setOpen(true)}><Sparkles aria-hidden="true" />Help me write {label}</button>
        {previous !== null && <button type="button" className="text-button" onClick={undo}>Put back what was there</button>}
      </div>
    )
  }
  return (
    <div className="field-help open" role="group" aria-label={`Help with ${label}`}>
      <input aria-label={`What should change in ${label}? (optional)`} placeholder="What should change? (optional)" value={request} maxLength={500}
        onChange={(event) => setRequest(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); void rewrite() } }} />
      <button type="button" className="button" disabled={busy} onClick={() => void rewrite()}>{busy ? 'Writing…' : 'Rewrite'}</button>
      <button type="button" className="text-button" disabled={busy} onClick={() => setOpen(false)}>Cancel</button>
      {error && <p className="field-help-error" role="alert">{error}</p>}
    </div>
  )
}
