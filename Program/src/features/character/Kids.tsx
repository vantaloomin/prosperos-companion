import { useState, type FormEvent } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Pencil, Plus, UserMinus } from 'lucide-react'
import { api } from '../../api'
import type { Kid, KidsView } from '../../types'
import { Field } from '../../components/Fields'
import { Notice } from '../../components/Feedback'
import { Stepper } from '../../components/NumberFields'
import { WhyItWent } from '../today/WhyItWent'
import { firstName } from './panelText'
import { KID_RELATIONS, KIDS_KEY, MAX_KID_AGE, kidAgeChoice, kidChange, kidForm, kidLine, kidSaved, kidsHint, madeUpLine, otherHint, parentChoice, removedLine, standingLine, whereHint, whereLabel, wherePick } from './familyText'

type KidsChange = { pattern?: string; remove?: string; restore?: string; other?: string; other_name?: string; other_pronouns?: string }
/** A confirmation or error, shown next to what it is about: the kids list or their other parent. */
type Feedback = { tone: 'info' | 'error'; text: string; at?: 'kids' | 'other' } | null
export type Removed = { id: string; name: string } | null

/** Companions who already have kids (companion/life/kids.py): their children, where they live and their other parent.
 * The app decides from their description; the user can add a child by hand, change a child's name, age or whether
 * they're a son or daughter, take a child out of their life, and change where the kids live and who their other
 * parent is. */
export function Kids({ view, name, removed, setRemoved }: { view: KidsView; name: string; removed: Removed; setRemoved: (removed: Removed) => void }) {
  const client = useQueryClient()
  const [feedback, setFeedback] = useState<Feedback>(null)
  const [adding, setAdding] = useState(false)
  const save = async (change: KidsChange, after: Removed = null, at: 'kids' | 'other' = 'kids') => {
    setFeedback(null)
    try {
      client.setQueryData(KIDS_KEY, await api<KidsView>('/life/steps/kids', change, 'PUT'))
      setRemoved(after)
      return true
    } catch (failure) {
      setFeedback({ tone: 'error', text: failure instanceof Error ? failure.message : 'That was not saved.', at })
      return false
    }
  }
  const open = () => { setFeedback(null); setAdding(true) }
  const kids = view.kids ?? []
  return (
    <div className="kids-block">
      <h3 id="kids-heading">{kids.length === 1 ? 'Their child' : 'Their children'}</h3>
      <ul className="person-list" aria-labelledby="kids-heading">
        {kids.map((kid) => <KidCard key={kid.id} kid={kid} setFeedback={setFeedback}
          remove={() => void save({ remove: kid.id }, { id: kid.id, name: kid.name })} />)}
      </ul>
      <p className="subtle">{kidsHint(view, name)}</p>
      <KidsNotices removed={removed} feedback={feedback?.at === 'other' ? null : feedback} name={name} undo={(id) => void save({ restore: id })} />
      {view.can_add && (adding
        ? <KidForm name={name} setFeedback={setFeedback} onDone={() => setAdding(false)} />
        : <button type="button" className="button kids-add" onClick={open}><Plus aria-hidden="true" />Add a child</button>)}
      <Standing view={view} name={name} />
      {view.consequence_id && <WhyItWent id={view.consequence_id} />}
      <OtherField view={view} name={name} save={(change) => save(change, null, 'other')} setFeedback={setFeedback} />
      <div aria-live="polite">{feedback?.at === 'other' && <Notice tone={feedback.tone}>{feedback.text}</Notice>}</div>
      <WhereField view={view} name={name} save={(change) => void save(change)} />
    </div>
  )
}

/** Under the list: Undo for a child just taken out, and what happened to the last change to a child. */
function KidsNotices({ removed, feedback, name, undo }: { removed: Removed; feedback: Feedback; name: string; undo: (id: string) => void }) {
  return (
    <div aria-live="polite">
      {removed && <Notice action={<button type="button" className="text-button" onClick={() => undo(removed.id)}>Undo</button>}>
        {removedLine(removed.name, name)}</Notice>}
      {feedback && <Notice tone={feedback.tone}>{feedback.text}</Notice>}
    </div>
  )
}

/** For a companion with no kids of their own: a way to add one by hand, the way a pet is added. */
export function NoKids({ name }: { name: string }) {
  const [adding, setAdding] = useState(false)
  const [feedback, setFeedback] = useState<Feedback>(null)
  return (
    <div className="kids-block">
      {adding
        ? <KidForm name={name} setFeedback={setFeedback} onDone={() => setAdding(false)} />
        : <div className="kids-none">
          <p className="subtle">{firstName(name)} has no children of their own.</p>
          <button type="button" className="button" onClick={() => { setFeedback(null); setAdding(true) }}><Plus aria-hidden="true" />Add a child</button>
        </div>}
      <div aria-live="polite">{feedback && <Notice tone={feedback.tone}>{feedback.text}</Notice>}</div>
    </div>
  )
}

function KidCard({ kid, remove, setFeedback }: { kid: Kid; remove: () => void; setFeedback: (feedback: Feedback) => void }) {
  const [editing, setEditing] = useState(false)
  if (editing) return <li className="person-card kid-card kid-editing"><KidForm kid={kid} setFeedback={setFeedback} onDone={() => setEditing(false)} /></li>
  return (
    <li className="person-card kid-card">
      <p>{kidLine(kid)}</p>
      <div className="person-actions">
        <button type="button" className="text-button" aria-label={`Edit ${kid.name}`} onClick={() => { setFeedback(null); setEditing(true) }}><Pencil aria-hidden="true" />Edit</button>
        <button type="button" className="text-button" aria-label={`Take ${kid.name} out of their life`} onClick={remove}>
          <UserMinus aria-hidden="true" />Remove
        </button>
      </div>
    </li>
  )
}

/** Adding a child (anything left out the app picks), or changing one's name, age or whether they're a son or daughter. */
function KidForm({ kid, name = '', setFeedback, onDone }: { kid?: Kid; name?: string; setFeedback: (feedback: Feedback) => void; onDone: () => void }) {
  const client = useQueryClient()
  const form = kidForm(kid)
  const [kidName, setKidName] = useState(form.name)
  const [pronouns, setPronouns] = useState(form.pronouns)
  const [age, setAge] = useState(form.age)
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setFeedback(null)
    try {
      const view = await api<KidsView>(form.path, kidChange(kid, kidName, pronouns, age), form.method)
      client.setQueryData(KIDS_KEY, view)
      setFeedback({ tone: 'info', text: kidSaved(kid, view) })
      onDone()
    } catch (failure) { setFeedback({ tone: 'error', text: failure instanceof Error ? failure.message : 'That was not saved.' }) }
  }
  return (
    <form className="rename-form home-add kid-form" onSubmit={(event) => void submit(event)} aria-label={form.title}>
      {form.adding && <p className="subtle">A child {firstName(name)} already has. Anything you leave blank, the app picks.</p>}
      <div className="kid-field">
        <label htmlFor={`${form.prefix}-name`}>Name</label>
        <input id={`${form.prefix}-name`} value={kidName} maxLength={60} required={!form.adding} placeholder={form.placeholder}
          autoComplete="off" onChange={(event) => setKidName(event.target.value)} />
      </div>
      <div className="kid-field">
        <label htmlFor={`${form.prefix}-relation`}>Son or daughter</label>
        <select id={`${form.prefix}-relation`} value={pronouns} onChange={(event) => setPronouns(event.target.value)}>
          {form.adding && <option value="">Let the app pick</option>}
          {KID_RELATIONS.map((item) => <option key={item.pronouns} value={item.pronouns}>{item.label}</option>)}
        </select>
      </div>
      <Stepper label="Age" value={age} min={form.youngest} max={MAX_KID_AGE} onChange={setAge} format={kidAgeChoice}
        hint={age < 0 ? 'Leave it and the app picks an age that fits them.' : undefined} />
      <div className="rename-row kid-actions">
        <button type="submit" className="button primary">{form.submit}</button>
        <button type="button" className="button quiet" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}

/** Their other parent: someone in their circle, someone else the user names, or nobody. Saved on change, except
 * someone new, who needs a name first. */
function OtherField({ view, name, save, setFeedback }: { view: KidsView; name: string; save: (change: KidsChange) => Promise<boolean>; setFeedback: (feedback: Feedback) => void }) {
  const [naming, setNaming] = useState(false)
  const [otherName, setOtherName] = useState('')
  const [pronouns, setPronouns] = useState('')
  const value = naming ? 'new' : view.other?.id ?? 'none'
  const pick = (picked: string) => {
    setFeedback(null)
    if (picked === 'new') { setNaming(true); return }
    setNaming(false)
    void save({ other: picked })
  }
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!otherName.trim()) return
    if (await save({ other: 'new', other_name: otherName.trim(), ...(pronouns ? { other_pronouns: pronouns } : {}) })) {
      setNaming(false)
      setOtherName('')
      setFeedback({ tone: 'info', text: `Saved. ${firstName(otherName.trim())} is their other parent now.`, at: 'other' })
    }
  }
  return <>
    <Field label="Their other parent" hint={naming ? undefined : otherHint(view, name)}>
      {(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} value={value} onChange={(event) => pick(event.target.value)}>
          {(view.others ?? []).map((person) => <option key={person.id} value={person.id}>{parentChoice(person)}</option>)}
          <option value="new">Someone else…</option>
          <option value="none">Nobody, {firstName(name)} is raising them alone</option>
        </select>
      )}
    </Field>
    {naming && (
      <form className="rename-form home-add kid-form" onSubmit={(event) => void submit(event)} aria-label="Name their other parent">
        {view.other?.made && <p className="subtle">{madeUpLine(view.other.name)}</p>}
        <div className="kid-field">
          <label htmlFor="kids-other-name">Name</label>
          <input id="kids-other-name" value={otherName} maxLength={80} required autoComplete="off" onChange={(event) => setOtherName(event.target.value)} />
        </div>
        <div className="kid-field">
          <label htmlFor="kids-other-pronouns">Their mom or dad</label>
          <select id="kids-other-pronouns" value={pronouns} onChange={(event) => setPronouns(event.target.value)}>
            <option value="">{view.other?.made ? 'Keep as it is' : 'Let the app pick'}</option>
            <option value="she/her">Mom</option>
            <option value="he/him">Dad</option>
            <option value="they/them">Parent</option>
          </select>
        </div>
        <div className="rename-row kid-actions">
          <button type="submit" className="button primary">Save</button>
          <button type="button" className="button quiet" onClick={() => setNaming(false)}>Cancel</button>
        </div>
      </form>
    )}
  </>
}

/** Undo for the last child taken out of their life, once the list of their kids has gone. */
export function KidsUndo({ removed, setRemoved, name }: { removed: Removed; setRemoved: (removed: Removed) => void; name: string }) {
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
        {removedLine(removed.name, name)}</Notice>
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
    <Field label={whereLabel(view)} hint={whereHint(view, name)}>
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
