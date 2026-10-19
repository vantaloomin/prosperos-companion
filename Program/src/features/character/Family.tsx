import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { FamilyView, Journey, KidsView, OurChild, OursView } from '../../types'
import { Field, Toggle } from '../../components/Fields'
import { Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { WhyItWent } from '../today/WhyItWent'
import { firstName } from './panelText'
import { STEPS_KEY, stepDate } from './stepsText'
import { FAMILY_KEY, KIDS_KEY, OURS_KEY, appPick, arrivalText, decidedHint, journeyLine, nameHint, outcomeSummary, routeHint, splitLine, wantsHint } from './familyText'
import { Kids, KidsUndo, type Removed } from './Kids'
import { HowItWent, OurChildren } from './OurChildren'

type FamilyChange = { wants?: string; route?: string; decided?: boolean; name?: string }
type Save = (change: FamilyChange) => void

/** Wanting children (companion/life/parenthood.py): whether they want children, and for a romance how a child would
 * come for you two and whether you have decided to start a family; first, the kids they already have
 * (companion/life/kids.py), and your own children with them (companion/life/our_child.py). The app picks each one;
 * the user can change it. */
export function Family({ name }: { name: string }) {
  const { error, view, theirs, own } = useFamily()
  const [removed, setRemoved] = useState<Removed>(null)
  if (error) return <ErrorNotice error={error} />
  if (!view && !theirs && !own && !removed) return null
  return (
    <section id="family" className="home-panel steps-panel family-panel" aria-labelledby="family-heading">
      <h2 id="family-heading">Family</h2>
      {theirs ? <Kids view={theirs} name={name} removed={removed} setRemoved={setRemoved} />
        : <KidsUndo removed={removed} setRemoved={setRemoved} />}
      {own && <OurChildren view={own} family={view} name={name} howItWent={(child) => <Arrival child={child} journey={view?.journey} name={name} />} />}
      <Together view={view} own={own} name={name} headed={Boolean(theirs || own)} />
    </section>
  )
}

/** What they want and a family together; while you two are split up, one line saying it comes back. */
function Together({ view, own, name, headed }: { view: FamilyView | null; own: OursView | null; name: string; headed: boolean }) {
  if (own?.custody?.split) return <p className="subtle">{splitLine(own.custody, name)}</p>
  return view && <Wishes view={view} name={name} headed={headed} folded={Boolean(own)} />
}

/** The panel's three parts, each only when it has something to show. */
function useFamily() {
  const query = useQuery({ queryKey: FAMILY_KEY, queryFn: () => api<FamilyView>('/life/steps/family') })
  const kids = useQuery({ queryKey: KIDS_KEY, queryFn: () => api<KidsView>('/life/steps/kids') })
  const ours = useQuery({ queryKey: OURS_KEY, queryFn: () => api<OursView>('/life/steps/ours') })
  return {
    error: query.error, view: shownOnly(query.data), theirs: shownOnly(kids.data), own: shownOnly(ours.data),
  }
}

function shownOnly<T extends { shown: boolean }>(data: T | undefined): T | null {
  return data?.shown ? data : null
}

/** Under a child's card: how they came, folded ("Born Mar 3, 2028 · Show how it went"), when the journey that brought
 * them is the one the panel has; else just the day. */
function Arrival({ child, journey, name }: { child: OurChild; journey?: Journey | null; name: string }) {
  if (!journey || journey.status !== 'home' || journey.name !== child.name) {
    return <p className="subtle">{arrivalText(child, undefined, stepDate)}</p>
  }
  return <HowItWent child={child} route={journey.route}><OnTheWay journey={journey} name={name} save={() => undefined} named={false} /></HowItWent>
}

/** What they want, and for a romance how a child would come and whether you two have decided; under its own heading
 * when their kids come first. */
function Wishes({ view, name, headed, folded }: { view: FamilyView; name: string; headed: boolean; folded: boolean }) {
  const client = useQueryClient()
  const [error, setError] = useState('')
  const save = async (change: FamilyChange) => {
    setError('')
    try {
      client.setQueryData(FAMILY_KEY, await api<FamilyView>('/life/steps/family', change, 'PUT'))
      void client.invalidateQueries({ queryKey: STEPS_KEY })
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'That was not saved.') }
  }
  return <>
    {headed && <h3 className="family-subheading">{view.romance ? 'A family together' : 'More children'}</h3>}
    <WantsField view={view} name={name} save={(change) => void save(change)} />
    {view.romance && view.routes && <TogetherFields view={view} name={name} save={(change) => void save(change)} />}
    {view.journey && !(folded && view.journey.status === 'home') && <OnTheWay journey={view.journey} name={name} save={(change) => void save(change)} />}
    {error && <Notice tone="error">{error}</Notice>}
  </>
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
    {!view.journey || view.journey.status === 'planned' ? <Field label="If you two start a family" hint={`Picked by the app from you and ${firstName(name)}: who could carry a baby, your ages, money and the times you live in. Change it until a baby is on the way.`}>
      {(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} value={set ? view.route : 'auto'} onChange={(event) => save({ route: event.target.value })}>
          <option value="auto">{appPick(set ? 'what fits you two' : label)}</option>
          {routes.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
        </select>
      )}
    </Field> : <div className="field">
      <span className="label-row"><span className="field-label">If you two start a family</span></span>
      <p className="field-value">{label}</p>
      <small className="subtle">{routeHint(view.journey)}</small>
    </div>}
    {view.route_consequence_id && !set && <WhyItWent id={view.route_consequence_id} />}
    <Toggle label={decided} checked={Boolean(view.decided_on)} disabled={!view.can_decide} hint={decidedHint(view, name)}
      onChange={(change) => save({ decided: change })} />
  </>
}

/** Expecting or adopting together (companion/life/expecting.py): where it stands, the stages with their days, and the
 * child's name once known, which the user can change. */
function OnTheWay({ journey, name, save, named = true }: { journey: Journey; name: string; save: Save; named?: boolean }) {
  return (
    <div className="steps-detail family-journey">
      {named && <p className="steps-line">{journeyLine(journey, name, stepDate)}</p>}
      {journey.stages.length > 0 && (
        <ol className="steps-list">
          {journey.stages.map((item) => (
            <li key={item.key}>
              <strong className={item.done ? undefined : 'step-pending'}>{item.label}</strong> <span className="subtle">· {stageDate(item)}</span>
            </li>
          ))}
        </ol>
      )}
      {named && journey.name && <ChildName key={journey.name} journey={journey} name={name} save={save} />}
      {(journey.outcomes ?? journey.consequences.map((id) => ({ key: '', id }))).map((item) => <WhyItWent key={item.id} id={item.id} summary={outcomeSummary(item.key, journey.route)} />)}
    </div>
  )
}

function stageDate(item: Journey['stages'][number]): string {
  if (item.done) return stepDate(item.date ?? '')
  return item.date ? `around ${stepDate(item.date)}` : 'no date yet'
}

function ChildName({ journey, name, save }: { journey: Journey; name: string; save: Save }) {
  const [value, setValue] = useState(journey.name ?? '')
  const submit = () => { const next = value.trim(); if (next && next !== journey.name) save({ name: next }) }
  return (
    <form className="rename-form" onSubmit={(event) => { event.preventDefault(); submit() }}>
      <label htmlFor="child-name">Their name</label>
      <div className="rename-row">
        <input id="child-name" value={value} maxLength={40} aria-describedby="child-name-hint" onChange={(event) => setValue(event.target.value)} />
        <button type="submit" className="button primary" disabled={!value.trim() || value.trim() === journey.name}>Save</button>
      </div>
      <small id="child-name-hint" className="subtle">{nameHint(journey, name)}</small>
    </form>
  )
}
