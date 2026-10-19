import { useState, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { Custody, FamilyView, OurChild, OursView } from '../../types'
import { Field, Toggle } from '../../components/Fields'
import { Notice } from '../../components/Feedback'
import { WhyItWent } from '../today/WhyItWent'
import { STEPS_KEY, stepDate } from './stepsText'
import { FAMILY_KEY, OURS_KEY, anotherHint, appPick, arrivalText, careHint, custodyHint, ourChildLine, sheetText } from './familyText'

type OursChange = { care?: string; child?: string; name?: string; custody?: string }

/** Our child (companion/life/our_child.py): each child of yours with them as a card (who they are lately, the
 * milestones so far, and how they came, folded away), who looks after them, and another child. Words only: no
 * picture of a child, anywhere. */
export function OurChildren({ view, family, name, howItWent }: {
  view: OursView; family: FamilyView | null; name: string; howItWent: (child: OurChild) => ReactNode
}) {
  const client = useQueryClient()
  const [error, setError] = useState('')
  const save = async (change: OursChange) => {
    setError('')
    try {
      client.setQueryData(OURS_KEY, await api<OursView>('/life/steps/ours', change, 'PUT'))
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'That was not saved.') }
  }
  const saveFamily = async (another: boolean) => {
    setError('')
    try {
      client.setQueryData(FAMILY_KEY, await api<FamilyView>('/life/steps/family', { another }, 'PUT'))
      void client.invalidateQueries({ queryKey: STEPS_KEY })
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'That was not saved.') }
  }
  const young = view.children.filter((child) => !child.grown)
  return (
    <div className="kids-block ours-block">
      <h3 id="ours-heading">{view.children.length === 1 ? 'Your child' : 'Your children'}</h3>
      <ul className="person-list" aria-labelledby="ours-heading">
        {view.children.map((child) => (
          <ChildCard key={child.id} child={child} name={name} save={(change) => void save(change)}>{howItWent(child)}</ChildCard>
        ))}
      </ul>
      {young.length > 0 && <Arrangements view={view} name={name} save={(change) => void save(change)} />}
      {family && (family.another_on || family.can_decide_another) && (
        <Toggle label={family.another_on ? `Another child, since ${stepDate(family.another_on)}` : 'Another child'}
          checked={Boolean(family.another_on)} disabled={!family.can_decide_another} hint={anotherHint(family, name)}
          onChange={(value) => void saveFamily(value)} />
      )}
      <div aria-live="polite">{error && <Notice tone="error">{error}</Notice>}</div>
    </div>
  )
}

/** One child: name, age and who they are lately; the milestones so far and how they came fold away. */
function ChildCard({ child, name, save, children }: {
  child: OurChild; name: string; save: (change: OursChange) => void; children: ReactNode
}) {
  return (
    <li className="person-card kid-card our-child-card">
      <p><strong>{ourChildLine(child)}</strong></p>
      {child.grown ? <p className="subtle">Grown up now, and in {name.split(' ')[0]}'s circle.</p> : <>
        {sheetText(child) && <p>{sheetText(child)}</p>}
        {child.quirk && <p className="subtle">{child.quirk}</p>}
      </>}
      {child.latest && <p className="subtle pet-line"><span className="pet-line-label">Latest ·</span> {child.latest.label}, {stepDate(child.latest.date)}</p>}
      {child.milestones.length > 1 && (
        <details className="our-child-more">
          <summary>All {child.milestones.length} milestones</summary>
          <ol className="steps-list">
            {child.milestones.map((item) => <li key={item.key}><strong>{item.label}</strong> <span className="subtle">· {stepDate(item.date)}</span></li>)}
          </ol>
        </details>
      )}
      {children}
      <Rename child={child} save={save} />
    </li>
  )
}

/** "Born Mar 3, 2028 · Show how it went": the journey that brought them, folded under the card. */
export function HowItWent({ child, route, children }: { child: OurChild; route?: string; children: ReactNode }) {
  return (
    <details className="our-child-more">
      <summary>{arrivalText(child, route, stepDate)} · Show how it went</summary>
      {children}
    </details>
  )
}

function Rename({ child, save }: { child: OurChild; save: (change: OursChange) => void }) {
  const [value, setValue] = useState(child.name)
  const id = `rename-${child.id}`
  return (
    <details className="our-child-more">
      <summary>Rename</summary>
      <form className="rename-form" onSubmit={(event) => { event.preventDefault(); const next = value.trim(); if (next && next !== child.name) save({ child: child.id, name: next }) }}>
        <label htmlFor={id} className="field-label">Their name</label>
        <div className="rename-row">
          <input id={id} value={value} maxLength={40} onChange={(event) => setValue(event.target.value)} />
          <button type="submit" className="button primary" disabled={!value.trim() || value.trim() === child.name}>Save</button>
        </div>
      </form>
    </details>
  )
}

/** Who looks after them until the youngest starts school: the app's pick first, named. */
function CareField({ view, name, save }: { view: OursView; name: string; save: (change: OursChange) => void }) {
  const cares = view.cares ?? []
  const set = view.care_how === 'set'
  const label = cares.find((item) => item.key === view.care)?.label ?? ''
  return <>
    <Field label="Who looks after them" hint={careHint(view, name)}>
      {(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} value={set ? view.care : 'auto'} onChange={(event) => save({ care: event.target.value })}>
          <option value="auto">{appPick(set ? 'what fits you two' : label)}</option>
          {cares.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
        </select>
      )}
    </Field>
    {view.care_consequence_id && !set && <WhyItWent id={view.care_consequence_id} />}
  </>
}

/** For children under 18: where they live while their parents live apart, and who looks after them. */
function Arrangements({ view, name, save }: { view: OursView; name: string; save: (change: OursChange) => void }) {
  return <>
    {view.custody && <CustodyField custody={view.custody} name={name} save={save} />}
    {view.care_now && <CareField view={view} name={name} save={save} />}
  </>
}

/** Where they live while their parents live apart: after a breakup the app's pick first, named, then the others;
 * across cities, only who they stay with. */
function CustodyField({ custody, name, save }: { custody: Custody; name: string; save: (change: OursChange) => void }) {
  const set = custody.how === 'set'
  const label = custody.patterns.find((item) => item.key === custody.pattern)?.label ?? ''
  if (custody.patterns.length < 2) return <p className="subtle">{custodyHint(custody, name)}</p>
  return <>
    <Field label="Where they live" hint={custodyHint(custody, name)}>
      {(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} value={set ? custody.pattern : 'auto'} onChange={(event) => save({ custody: event.target.value })}>
          <option value="auto">{appPick(set ? 'what fits you two' : label)}</option>
          {custody.patterns.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
        </select>
      )}
    </Field>
    {custody.consequence_id && !set && <WhyItWent id={custody.consequence_id} />}
  </>
}
