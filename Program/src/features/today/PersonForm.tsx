import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { CareerSummary, CirclePerson } from '../../types'
import { AGE_CHOICES, RELATION_WORDS, aboutChange, aboutForm, aboutSaved, type AboutValues } from './circleText'

type Act = (action: () => Promise<unknown>, done: string) => Promise<boolean>

/** Changing someone in the circle, or adding someone by hand (`person` left out): name, how they know the companion,
 * pronouns, job, workplace, age, whether they live in town and a note the chat reads. The app picks anything left
 * blank when adding; when changing, only what changed is sent. */
export function PersonForm({ person, companion, act, onDone }: { person?: CirclePerson; companion: string; act: Act; onDone: () => void }) {
  const form = aboutForm(person)
  const [values, setValues] = useState<AboutValues>(form.values)
  const careers = useQuery({ queryKey: ['careers'], queryFn: () => api<CareerSummary[]>('/world/careers'), staleTime: Infinity })
  const jobs = [...new Set((careers.data ?? []).filter((career) => !career.adult).map((career) => career.name))].sort()
  const set = (change: Partial<AboutValues>) => setValues((current) => ({ ...current, ...change }))
  const prefix = `about-${person?.id ?? 'new'}`
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const change = aboutChange(form.values, values, !person)
    if (person && Object.keys(change).length === 0) { onDone(); return }
    const path = person ? `/life/circle/${person.id}/about` : '/life/circle/people'
    if (await act(() => api(path, change, person ? 'PUT' : 'POST'), aboutSaved(person, values.name.trim(), companion))) onDone()
  }
  return (
    <form className="rename-form home-add kid-form person-form" onSubmit={(event) => void submit(event)} aria-label={form.title(companion)}>
      {!person && <p className="subtle">Someone in {companion}'s life. Anything you leave blank, the app picks.</p>}
      <div className="kid-field">
        <label htmlFor={`${prefix}-name`}>Name</label>
        <input id={`${prefix}-name`} value={values.name} maxLength={60} required autoComplete="off" onChange={(event) => set({ name: event.target.value })} />
      </div>
      <div className="kid-field">
        <label htmlFor={`${prefix}-role`}>Who they are to {companion}</label>
        <input id={`${prefix}-role`} value={values.role} maxLength={40} required={!!person} list={`${prefix}-roles`} autoComplete="off"
          placeholder={person ? undefined : 'Friend'} onChange={(event) => set({ role: event.target.value })} />
        <datalist id={`${prefix}-roles`}>{RELATION_WORDS.map((word) => <option key={word} value={word} />)}</datalist>
      </div>
      <div className="kid-field">
        <label htmlFor={`${prefix}-pronouns`}>Pronouns</label>
        <select id={`${prefix}-pronouns`} value={values.pronouns} onChange={(event) => set({ pronouns: event.target.value })}>
          {!person && <option value="">Let the app pick</option>}
          <option value="she/her">she/her</option>
          <option value="he/him">he/him</option>
          <option value="they/them">they/them</option>
        </select>
      </div>
      <div className="kid-field">
        <label htmlFor={`${prefix}-job`}>Job</label>
        <input id={`${prefix}-job`} value={values.job} maxLength={60} list={`${prefix}-jobs`} autoComplete="off" aria-describedby={`${prefix}-job-hint`}
          onChange={(event) => set({ job: event.target.value })} />
        <datalist id={`${prefix}-jobs`}>{jobs.map((job) => <option key={job} value={job} />)}</datalist>
        <small id={`${prefix}-job-hint`}>In your words. Their hours follow the job; write Retired for none.</small>
      </div>
      <div className="kid-field">
        <label htmlFor={`${prefix}-employer`}>Where they work</label>
        <input id={`${prefix}-employer`} value={values.employer} maxLength={80} autoComplete="off" onChange={(event) => set({ employer: event.target.value })} />
      </div>
      <div className="kid-field">
        <label htmlFor={`${prefix}-age`}>Age</label>
        <select id={`${prefix}-age`} value={values.age} onChange={(event) => set({ age: event.target.value })}>
          {!person && <option value="">Let the app pick</option>}
          {AGE_CHOICES(form.values.age).map((age) => <option key={age} value={age}>{age}</option>)}
        </select>
      </div>
      <div className="kid-field">
        <label htmlFor={`${prefix}-local`}>Where they live</label>
        <select id={`${prefix}-local`} value={values.local} onChange={(event) => set({ local: event.target.value === 'away' ? 'away' : 'here' })}>
          <option value="here">In town</option>
          <option value="away">Out of town</option>
        </select>
      </div>
      <div className="kid-field">
        <label htmlFor={`${prefix}-note`}>About them</label>
        <textarea id={`${prefix}-note`} value={values.note} maxLength={300} rows={2} aria-describedby={`${prefix}-note-hint`}
          onChange={(event) => set({ note: event.target.value })} />
        <small id={`${prefix}-note-hint`}>{companion} keeps this in mind when they come up in chat.</small>
      </div>
      <div className="rename-row kid-actions">
        <button type="submit" className="button primary">{form.submit}</button>
        <button type="button" className="button quiet" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}
