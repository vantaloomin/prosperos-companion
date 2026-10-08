import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Sparkles } from 'lucide-react'
import { api } from '../../api'
import type { View } from '../../companion'
import type { CastDraft, CharacterDefinition, Companion, Connection } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { CharacterForm, type Start } from './Character'
import { givenName } from './castText'
import { refocus } from './refocus'

interface Props { townKey: string; go: (view: View) => void }

/** A townsperson the companion has met, or a dating match, becomes the main character, from a profile the user
 * reviews first. */
export function SwitchTo({ townKey, go }: Props) {
  const client = useQueryClient()
  const draft = useQuery({ queryKey: ['cast-draft', townKey], queryFn: () => api<CastDraft>(`/companion/cast/draft?key=${encodeURIComponent(townKey)}`), staleTime: Infinity, retry: false })
  const [start, setStart] = useState<Start | null>(null)
  if (draft.isPending) return <Loading label="Drafting their profile" />
  if (draft.isError) {
    return (
      <section className="page">
        <ErrorNotice error={draft.error} action={<button type="button" className="text-button" onClick={() => window.history.back()}>Go back</button>} />
      </section>
    )
  }
  const { person, stepping_back: old, matched } = draft.data
  const name = givenName(person.full)
  const current = start ?? { definition: draft.data.definition, drafted: false, attempt: 0 }
  const save = async (definition: CharacterDefinition) => {
    const saved = await api<Companion>('/companion/cast/switch', { key: townKey, definition })
    await refocus(client)
    return saved
  }
  return (
    <CharacterForm key={`switch-${current.attempt}`} companion={null} start={current} onRestart={() => setStart(null)} go={go} saved={null} onSaved={() => undefined}
      create={{
        save, label: old ? `Make ${name} the main character` : `Start talking to ${name}`,
        heading: <header className="page-header"><div>
          <h1>{person.full}</h1>
          <p className="subtle">{person.role.charAt(0).toUpperCase()}{person.role.slice(1)}, {person.neighborhood}. {matched ? `You matched with ${name}.` : `${old} has run into ${name} around town.`} Read their profile through and change anything you like before {old ? 'they take over' : 'you start talking'}.</p>
        </div></header>,
        notice: <Written old={old} name={name} townKey={townKey} written={current.drafted} onWritten={(definition) => setStart({ definition, drafted: true, attempt: current.attempt + 1 })} onReset={() => setStart(null)} />,
      }} />
  )
}

interface WrittenProps { old: string | null; name: string; townKey: string; written: boolean; onWritten: (definition: CharacterDefinition) => void; onReset: () => void }

/** What switching means, and an offer to have the text model write the sheet out in full. */
function Written({ old, name, townKey, written, onWritten, onReset }: WrittenProps) {
  const connection = useQuery({ queryKey: ['connection'], queryFn: () => api<{ connection: Connection | null }>('/connection').then((data) => data.connection) })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const write = async () => {
    setBusy(true)
    setError('')
    try {
      onWritten((await api<CastDraft>('/companion/cast/draft', { key: townKey })).definition)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'The profile could not be written.')
    } finally { setBusy(false) }
  }
  return (
    <div className="form-stack">
      <Notice>{name} becomes the main character, and the text model plays them from now on.{old ? ` ${old} steps back: everything you two shared stays, ${old} goes on living around town by simple rules, and you can switch back from the Character page.` : ''}</Notice>
      {written
        ? <p className="subtle">Written out by your text model. <button type="button" className="text-button inline" onClick={onReset}>Use the plain profile instead</button></p>
        : connection.data && <p className="subtle">This profile comes from what the town knows about {name}.{' '}
          <button type="button" className="text-button inline" disabled={busy} onClick={() => void write()}><Sparkles aria-hidden="true" />{busy ? 'Writing…' : 'Write it out with your text model'}</button></p>}
      {busy && <Notice>Writing their profile. A local model can take a minute or two.</Notice>}
      {error && <Notice tone="error">{error}</Notice>}
    </div>
  )
}
