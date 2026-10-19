import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { UserMinus } from 'lucide-react'
import { api } from '../../api'
import type { KidsView } from '../../types'
import { Field } from '../../components/Fields'
import { Notice } from '../../components/Feedback'
import { WhyItWent } from '../today/WhyItWent'
import { KIDS_KEY, appPick, kidLine, kidsHint, stepParentLine, whereHint } from './familyText'

type KidsChange = { pattern?: string; remove?: string }

/** Companions who already have kids (companion/life/kids.py): their children, where they live and their other parent.
 * The app decides from their description; the user can change where the kids live or take a child out of their life. */
export function Kids({ view, name }: { view: KidsView; name: string }) {
  const client = useQueryClient()
  const [notice, setNotice] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const save = async (change: KidsChange, done = '') => {
    setNotice(null)
    try {
      client.setQueryData(KIDS_KEY, await api<KidsView>('/life/steps/kids', change, 'PUT'))
      if (done) setNotice({ tone: 'info', text: done })
    } catch (failure) { setNotice({ tone: 'error', text: failure instanceof Error ? failure.message : 'That was not saved.' }) }
  }
  const kids = view.kids ?? []
  const stepParent = stepParentLine(view, name)
  return (
    <div className="kids-block">
      <h3 id="kids-heading">{kids.length === 1 ? 'Their child' : 'Their kids'}</h3>
      <ul className="person-list" aria-labelledby="kids-heading">
        {kids.map((kid) => (
          <li key={kid.id} className="person-card kid-card">
            <p>{kidLine(kid)}</p>
            <button type="button" className="text-button" aria-label={`Take ${kid.name} out of their life`}
              onClick={() => void save({ remove: kid.id }, `${kid.name} is no longer part of their life.`)}>
              <UserMinus aria-hidden="true" />Remove
            </button>
          </li>
        ))}
      </ul>
      <p className="subtle">{kidsHint(view, name)}</p>
      {view.consequence_id && <WhyItWent id={view.consequence_id} />}
      {stepParent && <p>{stepParent}</p>}
      <WhereField view={view} name={name} save={(change) => void save(change)} />
      <div aria-live="polite">{notice && <Notice tone={notice.tone}>{notice.text}</Notice>}</div>
    </div>
  )
}

/** Where the kids live: the app's pick first, named, then the others that fit who they live with. */
function WhereField({ view, name, save }: { view: KidsView; name: string; save: (change: KidsChange) => void }) {
  const patterns = view.patterns ?? []
  const set = view.pattern_how === 'set'
  const label = patterns.find((item) => item.key === view.pattern)?.label ?? ''
  if (patterns.length < 2) return <p className="subtle">{label}. {whereHint(view, name)}</p>
  return <>
    <Field label="Where the kids live" hint={whereHint(view, name)}>
      {(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} value={set ? view.pattern : 'auto'} onChange={(event) => save({ pattern: event.target.value })}>
          <option value="auto">{appPick(set ? 'what fits them' : label)}</option>
          {patterns.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
        </select>
      )}
    </Field>
    {view.pattern_consequence_id && !set && <WhyItWent id={view.pattern_consequence_id} />}
  </>
}
