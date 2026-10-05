import { useState, type FormEvent, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '../../api'
import { COMPANION_KEY, type View } from '../../companion'
import type { CharacterDefinition, CharacterVersion, Companion, Connection, Relationship } from '../../types'
import { Notice } from '../../components/Feedback'
import { Field, TextArea, TextInput } from '../../components/Fields'
import { RELATIONSHIPS, cleanDefinition, completeDefinition, emptyDefinition, guessTimezone, listTexts, timezones } from './definition'
import { fieldValue, withField, type DraftField, type FormState } from './drafting'
import { FieldHelp } from './FieldHelp'
import { Home } from './Home'
import { TraitEditor } from './TraitEditor'
import { LifeFields } from './LifeFields'
import { QuickStart } from './QuickStart'
import { scheduleProblems } from './schedule'
import { StudyImport } from './StudyImport'
import { SelfFacts } from './SelfFacts'

interface Start { definition: CharacterDefinition; drafted: boolean; attempt: number }

export function Character({ companion, go }: { companion: Companion | null; go: (view: View) => void }) {
  const [saved, setSaved] = useState<number | null>(null)
  // A new companion starts with the quick start; the form then reviews the draft or starts empty.
  const [start, setStart] = useState<Start | null>(null)
  const begin = (definition: CharacterDefinition, drafted: boolean) => setStart((current) => ({ definition, drafted, attempt: (current?.attempt ?? 0) + 1 }))
  if (!companion && !start) {
    return (
      <section className="page">
        <CharacterHeading companion={null} go={go} />
        <QuickStart onDraft={(definition) => begin(definition, true)} onManual={() => begin(emptyDefinition(guessTimezone()), false)} go={go} />
      </section>
    )
  }
  // Remount the form on a new version or a new draft so it never edits a stale definition.
  return <CharacterForm key={companion?.active_version_id ?? `new-${start?.attempt}`} companion={companion} start={start} onRestart={() => setStart(null)} go={go} saved={saved} onSaved={setSaved} />
}

interface FormProps { companion: Companion | null; start: Start | null; onRestart: () => void; go: (view: View) => void; saved: number | null; onSaved: (version: number) => void }

function CharacterForm({ companion, start, onRestart, go, saved, onSaved }: FormProps) {
  const client = useQueryClient()
  const connection = useQuery({ queryKey: ['connection'], queryFn: () => api<{ connection: Connection | null }>('/connection').then((data) => data.connection) })
  const [form, setForm] = useState<FormState>(() => initialForm(companion, start))
  const { definition, texts } = form
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [result, setResult] = useState<{ tone: 'info' | 'error'; text: string; conflict?: boolean } | null>(null)
  const set = (change: Partial<CharacterDefinition>) => setForm((current) => ({ ...current, definition: { ...current.definition, ...change } }))
  const setText = (key: keyof FormState['texts']) => (value: string) => setForm((current) => ({ ...current, texts: { ...current.texts, [key]: value } }))
  const problems = scheduleProblems(definition.schedule)
  const cleaned = () => cleanDefinition(definition, texts.interests, texts.themes, texts)
  // Rewriting one field with the text model, when one is connected.
  const help = (field: DraftField, label: string): ReactNode => connection.data
    ? <FieldHelp field={field} label={label} definition={cleaned} current={fieldValue(form, field)} apply={(value) => setForm((current) => withField(current, field, value))} />
    : null

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    const body = cleaned()
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
      <CharacterHeading companion={companion} go={go} />
      {!companion && <div className="start-notice"><StartNotice drafted={!!start?.drafted} onRestart={onRestart} /></div>}
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
        {help('identity', 'who they are')}
        <TextArea label="Personality" value={definition.personality} onChange={(personality) => set({ personality })} rows={4} maxLength={8000} />
        {help('personality', 'their personality')}
        <TextArea label="Voice" value={definition.voice} onChange={(voice) => set({ voice })} maxLength={4000} hint="How they talk: rhythm, humour, words they like." />
        {help('voice', 'their voice')}
        <TextArea label="Skills" value={texts.skills} onChange={setText('skills')} rows={4} hint="One per line. Concrete things they are good at, and a few they are only middling at." />
        {help('skills', 'their skills')}
        <TextArea label="Flaws" value={texts.flaws} onChange={setText('flaws')} rows={4} hint="One per line. Real flaws that show up in conversation make them feel like a person." />
        {help('flaws', 'their flaws')}
        <TextInput label="Interests" value={texts.interests} onChange={setText('interests')} hint="Separate with commas." />
        {help('interests', 'their interests')}
        <TextArea label="Background" value={definition.background} onChange={(background) => set({ background })} rows={4} maxLength={12000} />
        {help('background', 'their background')}
        <TextArea label="Appearance" value={definition.appearance} onChange={(appearance) => set({ appearance })} maxLength={4000} />
        {help('appearance', 'their appearance')}
        <TextArea label="Routine in their words" value={definition.routine} onChange={(routine) => set({ routine })} maxLength={8000} hint="How they describe a typical day. The weekly routine below is what their life actually follows." />
        {help('routine', 'their routine')}
        <LifeFields definition={definition} set={set} themes={texts.themes} setThemes={setText('themes')} help={help} />
        <TraitEditor traits={definition.emotional_traits} onChange={(emotional_traits) => set({ emotional_traits })} />
        <TextArea label="How they react to time apart" value={definition.absence_reaction} onChange={(absence_reaction) => set({ absence_reaction })} maxLength={2000}
          hint="Optional. Left empty, they are relaxed about time apart and never make you feel guilty for it." />
        {companion && <TextInput label="What changed (optional)" value={note} onChange={setNote} maxLength={500} />}
        <SaveFeedback result={result} saved={savedNow(saved, companion)} onReload={() => void client.invalidateQueries({ queryKey: COMPANION_KEY })} />
        {problems.length > 0 && <Notice tone="error">{problems.join(' ')}</Notice>}
        <div className="form-actions">
          <button type="submit" className="button primary" disabled={saving || !definition.name.trim() || problems.length > 0}>{companion ? 'Save new version' : 'Create companion'}</button>
        </div>
      </form>
      {companion && <Home name={companion.version.name} />}
      {companion && <SelfFacts name={companion.version.name} />}
      {companion && <Versions current={companion.active_version_id} />}
    </section>
  )
}

function initialForm(companion: Companion | null, start: Start | null): FormState {
  const definition = companion ? completeDefinition(companion.version.definition) : start?.definition ?? emptyDefinition(guessTimezone())
  return { definition, texts: listTexts(definition) }
}

/** The version just saved, while the form still shows it. */
function savedNow(saved: number | null, companion: Companion | null): number | null {
  return saved !== null && saved === companion?.version.number ? saved : null
}

function StartNotice({ drafted, onRestart }: { drafted: boolean; onRestart: () => void }) {
  if (drafted) {
    return <Notice action={<button type="button" className="text-button" onClick={onRestart}>Start over</button>}>This is a draft from your text model. Read it through and change anything you like; nothing is saved until you create the companion.</Notice>
  }
  return <p className="subtle"><button type="button" className="text-button inline" onClick={onRestart}>Back to the quick start</button></p>
}

function CharacterHeading({ companion, go }: { companion: Companion | null; go: (view: View) => void }) {
  return (<>
    <header className="page-header">
      <div>
        <h1>{companion ? companion.version.name : 'Create your companion'}</h1>
        <p className="subtle">{companion ? `Version ${companion.version.number}. Saving creates a new version that applies from the next reply; earlier messages keep the version they used.` : 'Only a name is required, and you can change everything later.'}</p>
      </div>
      {companion && <button type="button" className="button" onClick={() => go('appearance')}>Look and LoRA</button>}
    </header>
    {!companion && <StudyImport />}
  </>)
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
