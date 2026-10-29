import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil } from 'lucide-react'
import { api } from '../../api'
import { Notice } from '../../components/Feedback'
import type { WorkLifeView } from '../../types'
import { Loading } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { AdminList } from '../today/AdminList'
import { WORK_KEY, eventDay, eventText, meterText, projectChange, projectField, timeOffText, yearOn } from './workText'
import { panelTitle } from './panelText'

// A rota's changing shifts go unsaid: the "This week:" line right below shows them (Iris).
const HOURS_TEXT = { staff: '', rota: '', freelance: ' Freelance work comes and goes, in busy and quiet spells.' }

/** The companion's job in plain words: the week, the project, late nights, time off and what changed lately. Nothing
 * for a companion without work in their week. */
export function WorkLife({ name }: { name: string }) {
  const query = useQuery({ queryKey: WORK_KEY, queryFn: () => api<{ work: WorkLifeView | null }>('/life/work') })
  const view = query.data?.work
  if (query.isSuccess && !view) return null
  return (
    <section id="work-life" className="home-panel work-panel" aria-labelledby="work-heading">
      <h2 id="work-heading">{panelTitle(name, view?.studying ? 'classes' : 'work life')}</h2>
      <p className="subtle">{introText(view)} You can change the project or its due date, and move a late night like anything on their calendar.</p>
      {query.isPending && <Loading label="Loading their work life" />}
      {query.isError && <ErrorNotice error={query.error} />}
      {view && <WorkDetails view={view} />}
    </section>
  )
}

/** The panel's intro, saying the app runs it and where the project comes from (Vanta could not tell): a student's
 * has classes and no raise (Iris). */
function introText(view: WorkLifeView | null | undefined): string {
  if (view?.studying) return 'Their studies run on their own: busy and light weeks, and one piece of coursework at a time that the app picks to fit what they study.'
  return `Their job runs on its own: busy and slow weeks, a raise once a year, and one project at a time that the app picks to fit their job and city.${view ? HOURS_TEXT[view.hours] : ''}`
}

function WorkDetails({ view }: { view: WorkLifeView }) {
  return <>
    <ul className="admin-state">{view.state.map((line) => <li key={line}>{line}</li>)}</ul>
    {view.level > 0 && view.status === 'working' && <WorkingOn view={view} />}
    {view.meter && <p className="subtle">{meterText(view.meter)}</p>}
    {view.late_nights.length > 0 && <><h3>{view.studying ? 'Studying late' : 'Staying late'}</h3><AdminList items={view.late_nights} inWorkPanel /></>}
    {view.level > 0 && view.status === 'working' && <>
      <h3>{view.studying ? 'Days off' : 'Time off'}</h3>
      <p className="subtle">{timeOffText(view.vacation, view.studying)}</p>
    </>}
    {view.events.length > 0 && <details className="wardrobe-group">
      <summary>What changed <span className="subtle">({view.events.length})</span></summary>
      <ul className="admin-state work-events">{view.events.map((event) => <li key={event.id}><span className="subtle">{eventDay(event)} · </span>{eventText(event)}</li>)}</ul>
    </details>}
  </>
}

/** What they're working on and when it is due, in the user's words until then; then the app picks the next one as
 * before. */
function WorkingOn({ view }: { view: WorkLifeView }) {
  const client = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState(projectField(view.project.title))
  const [due, setDue] = useState(view.project.due)
  const [notice, setNotice] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const save = async (change: { title?: string; due?: string }) => {
    try {
      client.setQueryData(WORK_KEY, await api<{ work: WorkLifeView | null }>('/life/work/project', change, 'PUT'))
      setNotice({ tone: 'info', text: change.title === '' ? 'The app picked it again.' : 'Saved. When it’s due, the app picks what comes next.' })
      setEditing(false)
    } catch (failure) { setNotice({ tone: 'error', text: failure instanceof Error ? failure.message : 'That was not saved.' }) }
  }
  const submit = (event: FormEvent) => {
    event.preventDefault()
    const change = projectChange(view, title, due)
    if (!Object.keys(change).length) { setEditing(false); return }
    void save(change)
  }
  const open = () => { setNotice(null); setTitle(projectField(view.project.title)); setDue(view.project.due); setEditing(true) }
  const label = view.studying ? 'What they’re working on for class' : 'What they’re working on'
  return <>
    {editing
      ? <form className="rename-form home-add kid-form" onSubmit={submit} aria-label={label}>
        <div className="kid-field">
          <label htmlFor="work-project">{label}</label>
          <input id="work-project" value={title} maxLength={120} autoComplete="off" required aria-describedby="work-project-hint" onChange={(event) => setTitle(event.target.value)} />
          <small id="work-project-hint">{view.own_project ? 'In your words.' : view.studying ? 'Picked by the app from coursework in what they study.' : 'Picked by the app from work someone in their job and city might do.'}</small>
        </div>
        <div className="kid-field">
          <label htmlFor="work-due">Due</label>
          <input id="work-due" type="date" value={due} min={view.today} max={view.today && yearOn(view.today)} required aria-describedby="work-due-hint" onChange={(event) => setDue(event.target.value)} />
          <small id="work-due-hint">When it’s due they wrap it up, and the app picks what comes next.</small>
        </div>
        <div className="rename-row kid-actions">
          <button type="submit" className="button primary">Save</button>
          <button type="button" className="button quiet" onClick={() => setEditing(false)}>Cancel</button>
        </div>
      </form>
      : <div className="person-actions">
        <button type="button" className="text-button" onClick={open}><Pencil aria-hidden="true" />Change what they’re working on</button>
        {(view.own_project || view.own_due) && <button type="button" className="text-button" onClick={() => void save({ title: '' })}>Let the app pick</button>}
      </div>}
    <div aria-live="polite">{notice && <Notice tone={notice.tone}>{notice.text}</Notice>}</div>
  </>
}
