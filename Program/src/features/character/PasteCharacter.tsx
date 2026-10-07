import { useState, type FormEvent } from 'react'
import { ClipboardPaste } from 'lucide-react'
import { api } from '../../api'
import type { Relationship } from '../../types'
import { Notice } from '../../components/Feedback'
import { Field, TextArea } from '../../components/Fields'
import { RELATIONSHIPS, guessTimezone } from './definition'
import { CardButton } from './CardButton'
import type { SplitResult } from './helper'

interface Props { connected: boolean; onSplit: (result: SplitResult) => void }

/** A character the user already has, pasted or opened from a card, split into the form's fields by their text model. */
export function PasteCharacter({ connected, onSplit }: Props) {
  const [text, setText] = useState('')
  const [relationship, setRelationship] = useState<Relationship>('friendship')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      onSplit(await api<SplitResult>('/companion/draft/split', { text, relationship, timezone: guessTimezone() }))
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'The character could not be split into fields.')
    } finally { setBusy(false) }
  }

  return (
    <section className="quick-start paste-character" aria-labelledby="paste-character-title">
      <h2 id="paste-character-title"><ClipboardPaste aria-hidden="true" />Already have a character?</h2>
      <p className="subtle">Paste all of them at once: notes, a bio, a character card or a scene. Your text model sorts it into the fields and fills in only what your text leaves out. You review everything before it is saved.</p>
      <form className="form-stack" onSubmit={submit}>
        <TextArea label="Your character" value={text} onChange={setText} maxLength={40000} rows={6}
          placeholder={'Name: Dana Whitfield\nDana is 34 and works nights as a nurse…'} hint="Their name, who they are, how they talk, their history: whatever you have, in any order." />
        <CardButton onText={setText} onError={setError} disabled={busy} />
        <Field label="Relationship" hint="Romance is only ever your choice.">
          {(id, hint) => (
            <select id={id} aria-describedby={hint} value={relationship} onChange={(event) => setRelationship(event.target.value as Relationship)}>
              {RELATIONSHIPS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          )}
        </Field>
        {busy && <Notice>Splitting your character into the fields. A local model can take a minute or two.</Notice>}
        {error && <Notice tone="error">{error}</Notice>}
        <div className="form-actions">
          <button type="submit" className="button primary" disabled={!connected || busy || !text.trim()}>{busy ? 'Splitting…' : 'Split into fields'}</button>
        </div>
      </form>
    </section>
  )
}
