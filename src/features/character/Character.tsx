import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '../../api'
import { COMPANION_KEY, type View } from '../../companion'
import type { CharacterDefinition, CharacterVersion, Companion, Relationship } from '../../types'
import { Notice } from '../../components/Feedback'
import { Field, TextArea, TextInput } from '../../components/Fields'
import { RELATIONSHIPS, cleanDefinition, completeDefinition, emptyDefinition, guessTimezone, timezones } from './definition'
import { TraitEditor } from './TraitEditor'

export function Character({ companion, go }: { companion: Companion | null; go: (view: View) => void }) {
  const [saved, setSaved] = useState<number | null>(null)
  // Remount the form on a new version so it never edits a stale definition.
  return <CharacterForm key={companion?.active_version_id ?? 'new'} companion={companion} go={go} saved={saved} onSaved={setSaved} />
}

function CharacterForm({ companion, go, saved, onSaved }: { companion: Companion | null; go: (view: View) => void; saved: number | null; onSaved: (version: number) => void }) {
  const client = useQueryClient()
  const [definition, setDefinition] = useState<CharacterDefinition>(() => companion ? completeDefinition(companion.version.definition) : emptyDefinition(guessTimezone()))
  const [interests, setInterests] = useState(definition.interests.join(', '))
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [result, setResult] = useState<{ tone: 'info' | 'error'; text: string; conflict?: boolean } | null>(null)
  const set = (change: Partial<CharacterDefinition>) => setDefinition((current) => ({ ...current, ...change }))

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    const body = cleanDefinition(definition, interests)
    try {
      const saved = companion
        ? await api<Companion>('/companion/versions', { definition: body, note, expected_version_id: companion.active_version_id })
        : await api<Companion>('/companion', body)
      client.setQueryData(COMPANION_KEY, saved)
      onSaved(saved.version.number)
      void client.invalidateQueries({ queryKey: ['versions'] })
      if (!companion) go('conversation')
    } catch (error) {
      setResult({ tone: 'error', text: error instanceof Error ? error.message : 'The character could not be saved.', conflict: error instanceof ApiError && error.status === 409 })
    } finally { setSaving(false) }
  }

  return (
    <section className="page">
      <CharacterHeading companion={companion} />
      <form className="form-stack" onSubmit={submit}>
        <div className="form-grid">
          <TextInput label="Name" value={definition.name} onChange={(name) => set({ name })} required maxLength={120} />
          <Field label="Relationship" hint="Romance is only ever your choice; warmth alone never changes it.">
            {(id, hint) => (
              <select id={id} aria-describedby={hint} value={definition.relationship} onChange={(event) => set({ relationship: event.target.value as Relationship })}>
                {RELATIONSHIPS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            )}
          </Field>
          <TextInput label="Their timezone" value={definition.timezone} onChange={(timezone) => set({ timezone })} list="timezones" maxLength={64} hint="Sets their day: when they wake, work and sleep." />
          <TextInput label="Where they live" value={definition.location} onChange={(location) => set({ location })} maxLength={200} hint="A fictional or real city for their life." />
        </div>
        <datalist id="timezones">{timezones().map((zone) => <option key={zone} value={zone} />)}</datalist>
        <TextArea label="Who they are" value={definition.identity} onChange={(identity) => set({ identity })} maxLength={4000} hint="Age, work, what matters to them." />
        <TextArea label="Personality" value={definition.personality} onChange={(personality) => set({ personality })} rows={4} maxLength={8000} />
        <TextArea label="Voice" value={definition.voice} onChange={(voice) => set({ voice })} maxLength={4000} hint="How they talk: rhythm, humour, words they like." />
        <TextInput label="Interests" value={interests} onChange={setInterests} hint="Separate with commas." />
        <TextArea label="Background" value={definition.background} onChange={(background) => set({ background })} rows={4} maxLength={12000} />
        <TextArea label="Appearance" value={definition.appearance} onChange={(appearance) => set({ appearance })} maxLength={4000} />
        <TextArea label="Routine" value={definition.routine} onChange={(routine) => set({ routine })} maxLength={8000} hint="A typical day and week. Their life will follow it." />
        <TraitEditor traits={definition.emotional_traits} onChange={(emotional_traits) => set({ emotional_traits })} />
        <TextArea label="How they react to time apart" value={definition.absence_reaction} onChange={(absence_reaction) => set({ absence_reaction })} maxLength={2000}
          hint="Optional. Left empty, they are relaxed about time apart and never make you feel guilty for it." />
        {companion && <TextInput label="What changed (optional)" value={note} onChange={setNote} maxLength={500} />}
        <SaveFeedback result={result} saved={saved !== null && saved === companion?.version.number ? saved : null} onReload={() => void client.invalidateQueries({ queryKey: COMPANION_KEY })} />
        <div className="form-actions">
          <button type="submit" className="button primary" disabled={saving || !definition.name.trim()}>{companion ? 'Save new version' : 'Create companion'}</button>
        </div>
      </form>
      {companion && <Versions current={companion.active_version_id} />}
    </section>
  )
}

function CharacterHeading({ companion }: { companion: Companion | null }) {
  return (
    <header className="page-header">
      <div>
        <h1>{companion ? companion.version.name : 'Create your companion'}</h1>
        <p className="subtle">{companion ? `Version ${companion.version.number}. Saving creates a new version that applies from the next reply; earlier messages keep the version they used.` : 'Only a name is required, and you can change everything later.'}</p>
      </div>
    </header>
  )
}

function SaveFeedback({ result, saved, onReload }: { result: { tone: 'info' | 'error'; text: string; conflict?: boolean } | null; saved: number | null; onReload: () => void }) {
  if (result) return <Notice tone={result.tone} action={result.conflict ? <button type="button" className="text-button" onClick={onReload}>Load the latest version</button> : undefined}>{result.text}</Notice>
  return saved ? <Notice>Saved version {saved}. It applies from the next reply.</Notice> : null
}

function Versions({ current }: { current: string }) {
  const versions = useQuery({ queryKey: ['versions'], queryFn: () => api<CharacterVersion[]>('/companion/versions') })
  if (!versions.data || versions.data.length < 2) return null
  return (
    <details className="versions">
      <summary>Earlier versions ({versions.data.length - 1})</summary>
      <ol reversed>
        {[...versions.data].reverse().map((version) => (
          <li key={version.id}>
            <span>Version {version.number}{version.id === current ? ' (current)' : ''}</span>
            <small>{new Date(version.effective_at).toLocaleString()}{version.note ? ` · ${version.note}` : ''}</small>
          </li>
        ))}
      </ol>
    </details>
  )
}
