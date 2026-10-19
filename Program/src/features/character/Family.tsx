import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { FamilyView } from '../../types'
import { Field, Toggle } from '../../components/Fields'
import { Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { WhyItWent } from '../today/WhyItWent'
import { firstName } from './panelText'
import { STEPS_KEY, stepDate } from './stepsText'
import { FAMILY_KEY, appPick, decidedHint, wantsHint } from './familyText'

type FamilyChange = { wants?: string; route?: string; decided?: boolean }
type Save = (change: FamilyChange) => void

/** Wanting children (companion/life/parenthood.py): whether they want children, and for a romance how a child would
 * come for you two and whether you have decided to start a family. The app picks each one; the user can change it. */
export function Family({ name }: { name: string }) {
  const client = useQueryClient()
  const query = useQuery({ queryKey: FAMILY_KEY, queryFn: () => api<FamilyView>('/life/steps/family') })
  const [error, setError] = useState('')
  const view = query.data
  if (query.isError) return <ErrorNotice error={query.error} />
  if (!view?.shown) return null
  const save = async (change: FamilyChange) => {
    setError('')
    try {
      client.setQueryData(FAMILY_KEY, await api<FamilyView>('/life/steps/family', change, 'PUT'))
      void client.invalidateQueries({ queryKey: STEPS_KEY })
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'That was not saved.') }
  }
  return (
    <section id="family" className="home-panel steps-panel family-panel" aria-labelledby="family-heading">
      <h2 id="family-heading">Family</h2>
      <WantsField view={view} name={name} save={(change) => void save(change)} />
      {view.romance && view.routes && <TogetherFields view={view} name={name} save={(change) => void save(change)} />}
      {error && <Notice tone="error">{error}</Notice>}
    </section>
  )
}

/** Whether they want children: the app's pick first, named, then the three answers. */
function WantsField({ view, name, save }: { view: FamilyView; name: string; save: Save }) {
  const set = view.wants_how === 'set'
  const label = view.wants_options.find((item) => item.key === view.wants)?.label ?? ''
  return <>
    <Field label="Wants children" hint={wantsHint(view, name)}>
      {(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} value={set ? view.wants : 'auto'} onChange={(event) => save({ wants: event.target.value })}>
          <option value="auto">{appPick(set ? 'what fits them' : label)}</option>
          {view.wants_options.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
        </select>
      )}
    </Field>
    {view.wants_consequence_id && !set && <WhyItWent id={view.wants_consequence_id} />}
  </>
}

/** For a romance: how a child would come for you two, and whether you have decided to start a family. */
function TogetherFields({ view, name, save }: { view: FamilyView; name: string; save: Save }) {
  const set = view.route_how === 'set'
  const routes = view.routes ?? []
  const label = routes.find((item) => item.key === view.route)?.label ?? ''
  const decided = view.decided_on ? `Starting a family, since ${stepDate(view.decided_on)}` : 'Starting a family'
  return <>
    <Field label="If you two start a family" hint={`Picked by the app from you and ${firstName(name)}: who could carry a baby, your ages, money and the times you live in. Change it before it starts.`}>
      {(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} value={set ? view.route : 'auto'} onChange={(event) => save({ route: event.target.value })}>
          <option value="auto">{appPick(set ? 'what fits you two' : label)}</option>
          {routes.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
        </select>
      )}
    </Field>
    {view.route_consequence_id && !set && <WhyItWent id={view.route_consequence_id} />}
    <Toggle label={decided} checked={Boolean(view.decided_on)} disabled={!view.can_decide} hint={decidedHint(view, name)}
      onChange={(change) => save({ decided: change })} />
  </>
}
