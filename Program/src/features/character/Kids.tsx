import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { UserMinus } from 'lucide-react'
import { api } from '../../api'
import type { KidsView } from '../../types'
import { Field } from '../../components/Fields'
import { Notice } from '../../components/Feedback'
import { WhyItWent } from '../today/WhyItWent'
import { KIDS_KEY, kidLine, kidsHint, standingLine, whereHint, wherePick } from './familyText'

type KidsChange = { pattern?: string; remove?: string; restore?: string }
export type Removed = { id: string; name: string } | null

/** Companions who already have kids (companion/life/kids.py): their children, where they live and their other parent.
 * The app decides from their description; the user can change where the kids live or take a child out of their life. */
export function Kids({ view, name, removed, setRemoved }: { view: KidsView; name: string; removed: Removed; setRemoved: (removed: Removed) => void }) {
  const client = useQueryClient()
  const [error, setError] = useState('')
  const save = async (change: KidsChange, after: Removed = null) => {
    setError('')
    try {
      client.setQueryData(KIDS_KEY, await api<KidsView>('/life/steps/kids', change, 'PUT'))
      setRemoved(after)
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'That was not saved.') }
  }
  const kids = view.kids ?? []
  return (
    <div className="kids-block">
      <h3 id="kids-heading">{kids.length === 1 ? 'Their child' : 'Their kids'}</h3>
      <ul className="person-list" aria-labelledby="kids-heading">
        {kids.map((kid) => (
          <li key={kid.id} className="person-card kid-card">
            <p>{kidLine(kid)}</p>
            <button type="button" className="text-button" aria-label={`Take ${kid.name} out of their life`}
              onClick={() => void save({ remove: kid.id }, { id: kid.id, name: kid.name })}>
              <UserMinus aria-hidden="true" />Remove
            </button>
          </li>
        ))}
      </ul>
      <p className="subtle">{kidsHint(view, name)}</p>
      <Standing view={view} name={name} />
      {view.consequence_id && <WhyItWent id={view.consequence_id} />}
      <WhereField view={view} name={name} save={(change) => void save(change)} />
      <div aria-live="polite">
        {removed && <Notice action={<button type="button" className="text-button" onClick={() => void save({ restore: removed.id })}>Undo</button>}>
          {removed.name} is no longer part of their life.</Notice>}
        {error && <Notice tone="error">{error}</Notice>}
      </div>
    </div>
  )
}

/** Undo for the last child taken out of their life, once the list of their kids has gone. */
export function KidsUndo({ removed, setRemoved }: { removed: Removed; setRemoved: (removed: Removed) => void }) {
  const client = useQueryClient()
  const [error, setError] = useState('')
  if (!removed) return null
  const undo = async () => {
    setError('')
    try {
      client.setQueryData(KIDS_KEY, await api<KidsView>('/life/steps/kids', { restore: removed.id }, 'PUT'))
      setRemoved(null)
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'That was not saved.') }
  }
  return (
    <div aria-live="polite">
      <Notice action={<button type="button" className="text-button" onClick={() => void undo()}>Undo</button>}>
        {removed.name} is no longer part of their life.</Notice>
      {error && <Notice tone="error">{error}</Notice>}
    </div>
  )
}

/** For a romance: "Step-parent · you live with Sam, so you're Major and Logan's step-parent." */
function Standing({ view, name }: { view: KidsView; name: string }) {
  const line = standingLine(view, name)
  return line && <p className="subtle pet-line kids-standing"><span className="pet-line-label">{line.label} ·</span> {line.text}</p>
}

/** Where the kids live: the app's pick first, named, then the others that fit who they live with. */
function WhereField({ view, name, save }: { view: KidsView; name: string; save: (change: KidsChange) => void }) {
  const patterns = view.patterns ?? []
  const set = view.pattern_how === 'set'
  const label = patterns.find((item) => item.key === view.pattern)?.label ?? ''
  if (patterns.length < 2) return <p className="subtle">{whereHint(view, name)}</p>
  return <>
    <Field label="Where the kids live" hint={whereHint(view, name)}>
      {(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} value={set ? view.pattern : 'auto'} onChange={(event) => save({ pattern: event.target.value })}>
          <option value="auto">{wherePick(view, name, label)}</option>
          {patterns.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
        </select>
      )}
    </Field>
    {view.pattern_consequence_id && !set && <WhyItWent id={view.pattern_consequence_id} />}
  </>
}
