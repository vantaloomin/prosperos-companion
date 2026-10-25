import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { PairTie, UntoldTie } from '../../types'
import { Field } from '../../components/Fields'
import { Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { PAIR_STAGES, howText, listedHow, modelHow, tieText } from '../memories/pairText'
import { firstName } from './panelText'

type TiesView = { ties: PairTie[]; untold: UntoldTie[] }
const TIES_KEY = ['companion-ties']

/** Who they know among your other companions (companion/memory/pairs.py), and how they know someone they don't yet:
 * the same once-only backstory a first group chat tells, without making a group. Filled in from where they live and
 * whether they have met, so saving is one click; after that only what happens between them changes it. */
export function WhoTheyKnow({ name }: { name: string }) {
  const client = useQueryClient()
  const query = useQuery({ queryKey: TIES_KEY, queryFn: () => api<TiesView>('/companion/ties') })
  const [saved, setSaved] = useState('')
  const { ties = [], untold = [] } = query.data ?? {}
  if (query.error) return <ErrorNotice error={query.error} />
  if (!ties.length && !untold.length && !saved) return null
  const first = firstName(name)
  const told = (view: TiesView, other: string) => {
    client.setQueryData(TIES_KEY, view)
    setSaved(other)
  }
  return (
    <section className="settings-section form-stack who-they-know" aria-labelledby="who-they-know-heading">
      <div>
        <h2 id="who-they-know-heading">Who {first} knows</h2>
        <p className="subtle">Your other companions {first} knows, and how close they feel. Time they spend together, in group chats or around town, changes it.</p>
      </div>
      <Known name={name} ties={ties} />
      {saved && <Notice>Saved. {first} and {firstName(saved)} know each other now.</Notice>}
      {untold.length > 0 && <TellTie name={name} untold={untold} onTold={told} />}
    </section>
  )
}

/** The companions they already know: "Mira and Billy: Close · Old bandmates". */
function Known({ name, ties }: { name: string; ties: PairTie[] }) {
  if (!ties.length) return <p className="subtle">{firstName(name)} doesn't know any of your other companions yet.</p>
  return (
    <ul className="network-list" aria-label={`Companions ${firstName(name)} knows`}>
      {ties.map((tie) => <li key={tie.companion_id}>{tieText(name, tie)}{tie.how && <span className="subtle"> · {listedHow(tie.how)}</span>}</li>)}
    </ul>
  )
}

/** One form for someone they don't know yet: who, how close, and how they know each other. */
function TellTie({ name, untold, onTold }: { name: string; untold: UntoldTie[]; onTold: (view: TiesView, other: string) => void }) {
  const [pick, setPick] = useState(untold[0].companion_id)
  const chosen = untold.find((item) => item.companion_id === pick) ?? untold[0]
  const [draft, setDraft] = useState({ for: chosen.companion_id, level: chosen.level, how: howText(chosen.how) })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const current = draft.for === chosen.companion_id ? draft : { for: chosen.companion_id, level: chosen.level, how: howText(chosen.how) }
  const first = firstName(name)
  const save = async () => {
    setBusy(true)
    setError(null)
    try {
      onTold(await api<TiesView>('/companion/ties', { companion_id: chosen.companion_id, level: current.level, how: modelHow(current.how).slice(0, 300) }), chosen.name)
    } catch (caught) {
      setError(caught as Error)
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="form-stack">
      <h3>Add someone {first} knows</h3>
      <div className="form-grid">
        <Field label="Who">
          {(id) => (
            <select id={id} value={chosen.companion_id} onChange={(event) => setPick(event.target.value)}>
              {untold.map((item) => <option key={item.companion_id} value={item.companion_id}>{item.name}</option>)}
            </select>
          )}
        </Field>
        <Field label="How close they are">
          {(id) => (
            <select id={id} value={current.level} onChange={(event) => setDraft({ ...current, level: Number(event.target.value) })}>
              {PAIR_STAGES.map((stage, index) => <option key={stage} value={index + 1}>{stage}</option>)}
            </select>
          )}
        </Field>
      </div>
      <Field label="How they know each other" hint={`Filled in for you. Once saved, only time ${first} and ${firstName(chosen.name)} spend together changes it.`}>
        {(id, hint) => <input id={id} aria-describedby={hint} value={current.how} maxLength={300} placeholder="e.g. Roommates in college" onChange={(event) => setDraft({ ...current, how: event.target.value })} />}
      </Field>
      {error && <ErrorNotice error={error} />}
      <div className="form-actions">
        <button type="button" className="button" disabled={busy} onClick={() => void save()}>{busy ? 'Saving…' : `Save how they know each other`}</button>
      </div>
    </div>
  )
}
