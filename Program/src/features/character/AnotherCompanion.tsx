import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { UserPlus } from 'lucide-react'
import { api } from '../../api'
import type { View } from '../../companion'
import type { CharacterDefinition, Companion } from '../../types'
import { Notice } from '../../components/Feedback'
import { sidecar } from '../sidecar/store'
import { CharacterForm, StartNotice, type Start } from './Character'
import { QuickStart } from './QuickStart'
import { emptyDefinition } from './definition'
import { refocus } from './refocus'

/** The Character page's way to someone new: made from scratch, with the same quick start and form as the first. */
export function AnotherSection({ name, go }: { name: string; go: (view: View) => void }) {
  return (
    <section className="settings-section form-stack" aria-labelledby="another-heading">
      <div>
        <h2 id="another-heading">Someone new</h2>
        <p className="subtle">Make another companion from scratch, written your way, to live in this world alongside {name}. {name} keeps every chat and memory and goes on with their own life, and you can switch between them any time.</p>
      </div>
      <div className="form-actions">
        <button type="button" className="button" onClick={() => go('another')}><UserPlus aria-hidden="true" />Create another companion</button>
      </div>
    </section>
  )
}

/** Another companion beside the main character (companion/cast.py `add`): they live in the same town, start in
 * the main character's city and time zone unless the user picks otherwise, and take over once created. */
export function AnotherCompanion({ companion, go }: { companion: Companion; go: (view: View) => void }) {
  const client = useQueryClient()
  const [start, setStart] = useState<Start | null>(null)
  const old = companion.version.name
  const { home_city: city = '', location = '', timezone } = companion.version.definition
  const begin = (definition: CharacterDefinition, drafted: boolean, split?: Start['split']) => {
    setStart((current) => ({ definition, drafted, split, attempt: (current?.attempt ?? 0) + 1 }))
    if (drafted && window.matchMedia?.('(min-width: 721px)').matches) sidecar.show()
  }
  const heading = (
    <header className="page-header">
      <div>
        <h1>Create another companion</h1>
        <p className="subtle">They live in this world alongside {old}. Nothing here is required, and you can change everything later.</p>
      </div>
      <div className="form-actions">
        <button type="button" className="text-button" onClick={() => go('character')}>Back to {old}</button>
      </div>
    </header>
  )
  if (!start) {
    return (
      <section className="page">
        {heading}
        <QuickStart another={{ name: old, city, timezone }} onDraft={(definition) => begin(definition, true)} onSplit={(result) => begin(result.definition, true, { filledIn: result.filled_in, homeCity: result.home_city })}
          onManual={() => begin({ ...emptyDefinition(timezone), home_city: city, location }, false)} go={go} />
      </section>
    )
  }
  const save = async (definition: CharacterDefinition) => {
    const saved = await api<Companion>('/companion/another', definition)
    await refocus(client)
    return saved
  }
  return (
    <CharacterForm key={`another-${start.attempt}`} companion={null} start={start} onRestart={() => setStart(null)} go={go} saved={null} onSaved={() => undefined}
      create={{
        save, label: 'Create companion', heading,
        notice: <>
          <StartNotice start={start} onRestart={() => setStart(null)} />
          <Notice>Once you create them, they become the main character. {old} steps back: everything you two shared stays, {old} goes on living around town, and you can switch back from the Character page or the Chats button.</Notice>
        </>,
      }} />
  )
}
