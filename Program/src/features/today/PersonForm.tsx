import { useState, type FormEvent, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown } from 'lucide-react'
import { api } from '../../api'
import type { CareerSummary, CirclePerson } from '../../types'
import { NOTE_MAX, RELATION_WORDS, aboutChange, aboutForm, aboutSaved, ageClamp, noteCount, placeWords, type AboutValues } from './circleText'
import { useCircleHome } from './useCircleHome'
import { PAIR_STAGES } from '../memories/pairText'

export type Act = (action: () => Promise<unknown>, done: string, local?: (feedback: { tone: 'info' | 'error'; text: string }) => void) => Promise<boolean>

interface Props {
  person?: CirclePerson
  companion: string
  act: Act
  onDone: (saved: boolean) => void
  /** Where the saved notice goes: inside the edited card (Iris R8). */
  local?: (feedback: { tone: 'info' | 'error'; text: string }) => void
}

/** Changing someone in the circle, or adding someone by hand (`person` left out): who they are, where they live,
 * their work and a note the chat reads. The app picks anything left blank when adding; when changing, only what
 * changed is sent. It fills the card it belongs to (Iris R1). */
export function PersonForm({ person, companion, act, onDone, local }: Props) {
  const form = aboutForm(person)
  const [values, setValues] = useState<AboutValues>(form.values)
  const careers = useQuery({ queryKey: ['careers'], queryFn: () => api<CareerSummary[]>('/world/careers'), staleTime: Infinity })
  const jobs = [...new Set((careers.data ?? []).filter((career) => !career.adult).map((career) => career.name))].sort()
  const set = (change: Partial<AboutValues>) => setValues((current) => ({ ...current, ...change }))
  const prefix = `about-${person?.id ?? 'new'}`
  const pick = person ? undefined : 'Let the app pick'
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const change = aboutChange(form.values, values, !person)
    if (person && Object.keys(change).length === 0) { onDone(false); return }
    const path = person ? `/life/circle/${person.id}/about` : '/life/circle/people'
    if (await act(() => api(path, change, person ? 'PUT' : 'POST'), aboutSaved(person, values.name.trim(), companion), local)) onDone(true)
  }
  const count = noteCount(values.note)
  return (
    <form className="circle-form" onSubmit={(event) => void submit(event)} aria-label={form.title(companion)}>
      {!person && <p className="subtle">Someone in {companion}'s life. Anything you leave blank, the app picks.</p>}
      <Text id={`${prefix}-name`} label="Name">
        <input id={`${prefix}-name`} value={values.name} maxLength={60} required autoComplete="off" autoFocus={!person} onChange={(event) => set({ name: event.target.value })} />
      </Text>
      <Text id={`${prefix}-role`} label={`Who they are to ${companion}`}>
        <Suggest id={`${prefix}-role`} value={values.role} options={RELATION_WORDS} placeholder={person ? undefined : 'Friend'} required={!!person} maxLength={40} onChange={(role) => set({ role })} />
      </Text>
      <Text id={`${prefix}-start`} label={`How close they are with ${companion}`} hint="Where the two of them start. It moves as their days go on.">
        <select id={`${prefix}-start`} value={values.start} aria-describedby={`${prefix}-start-hint`} onChange={(event) => set({ start: event.target.value })}>
          <option value="">Let the app pick</option>
          {PAIR_STAGES.map((stage, index) => <option key={stage} value={String(index + 1)}>{stage}</option>)}
        </select>
      </Text>
      <Basics prefix={prefix} values={values} set={set} adding={!person} current={form.values.age} />
      <div className="circle-form-row circle-form-work">
        <Text id={`${prefix}-job`} label="Job" hint="In your words, like Photography student or Retired. Their hours follow the job.">
          <Suggest id={`${prefix}-job`} value={values.job} options={jobs} placeholder={pick} maxLength={60} describedBy={`${prefix}-job-hint`} onChange={(job) => set({ job })} />
        </Text>
        <Text id={`${prefix}-employer`} label="Where they work">
          <input id={`${prefix}-employer`} value={values.employer} maxLength={80} autoComplete="off" placeholder={pick} onChange={(event) => set({ employer: event.target.value })} />
        </Text>
      </div>
      <Text id={`${prefix}-note`} label="About them" hint={`${companion} keeps this in mind when they come up in chat.${count ? ` ${count}` : ''}`}>
        <textarea id={`${prefix}-note`} value={values.note} maxLength={NOTE_MAX} rows={3} aria-describedby={`${prefix}-note-hint`}
          onChange={(event) => set({ note: event.target.value })} />
      </Text>
      <div className="rename-row circle-form-actions">
        <button type="submit" className="button primary">{form.submit}</button>
        <button type="button" className="button quiet" onClick={() => onDone(false)}>Cancel</button>
      </div>
    </form>
  )
}

interface BasicsProps { prefix: string; values: AboutValues; set: (change: Partial<AboutValues>) => void; adding: boolean; current: string }

/** Pronouns and age on one row, then where they live; "Let the app pick" for each when adding (Iris R2, R4, R5). */
function Basics({ prefix, values, set, adding, current }: BasicsProps) {
  const [ageNote, setAgeNote] = useState('')
  const blurAge = () => {
    const clamped = ageClamp(values.age, current)
    setAgeNote(clamped.note)
    if (clamped.value !== values.age) set({ age: clamped.value })
  }
  const pick = adding ? <option value="">Let the app pick</option> : null
  const place = placeWords(useCircleHome())
  return <>
    <div className="circle-form-row">
      <Text id={`${prefix}-pronouns`} label="Pronouns">
        <select id={`${prefix}-pronouns`} value={values.pronouns} onChange={(event) => set({ pronouns: event.target.value })}>
          {pick}
          <option value="she/her">she/her</option>
          <option value="he/him">he/him</option>
          <option value="they/them">they/them</option>
        </select>
      </Text>
      <Text id={`${prefix}-age`} label="Age" hint={ageNote || undefined}>
        <input id={`${prefix}-age`} value={values.age} inputMode="numeric" maxLength={4} autoComplete="off" placeholder={adding ? 'Let the app pick' : undefined}
          aria-describedby={ageNote ? `${prefix}-age-hint` : undefined} onBlur={blurAge}
          onChange={(event) => { setAgeNote(''); set({ age: event.target.value.replace(/\D/g, '') }) }} />
      </Text>
    </div>
    <Text id={`${prefix}-local`} label="Where they live">
      <select id={`${prefix}-local`} value={values.local} onChange={(event) => set({ local: placeOf(event.target.value) })}>
        {pick}
        <option value="here">{place.here}</option>
        <option value="away">{place.away}</option>
      </select>
    </Text>
  </>
}

const placeOf = (value: string): AboutValues['local'] => value === 'here' || value === 'away' ? value : ''

/** A label, the control and an optional hint (`{id}-hint`). */
function Text({ id, label, hint, children }: { id: string; label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="circle-field">
      <label htmlFor={id}>{label}</label>
      {children}
      {hint && <small id={`${id}-hint`}>{hint}</small>}
    </div>
  )
}

interface SuggestProps { id: string; value: string; options: string[]; onChange: (value: string) => void; placeholder?: string; required?: boolean; maxLength: number; describedBy?: string }

/** Free text with suggestions, drawn with the same chevron as the selects (Iris R3). */
function Suggest({ id, value, options, onChange, placeholder, required, maxLength, describedBy }: SuggestProps) {
  return (
    <span className="suggest">
      <input id={id} value={value} list={`${id}-list`} maxLength={maxLength} required={required} placeholder={placeholder} autoComplete="off"
        aria-describedby={describedBy} onChange={(event) => onChange(event.target.value)} />
      <ChevronDown aria-hidden="true" />
      <datalist id={`${id}-list`}>{options.map((option) => <option key={option} value={option} />)}</datalist>
    </span>
  )
}
