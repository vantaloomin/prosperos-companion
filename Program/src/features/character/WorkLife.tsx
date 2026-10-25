import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil } from 'lucide-react'
import { api } from '../../api'
import { Notice } from '../../components/Feedback'
import type { WorkLifeView } from '../../types'
import { Loading } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { AdminList } from '../today/AdminList'
import { WORK_KEY, eventDay, eventText, meterText, timeOffText } from './workText'
import { panelTitle } from './panelText'

const HOURS_TEXT = { staff: '', rota: ' Their shifts change each week.', freelance: ' Freelance work comes and goes, in busy and quiet spells.' }

/** The companion's job in plain words: the week, the project, late nights, time off and what changed lately. Nothing
 * for a companion without work in their week. */
export function WorkLife({ name }: { name: string }) {
  const query = useQuery({ queryKey: WORK_KEY, queryFn: () => api<{ work: WorkLifeView | null }>('/life/work') })
  const view = query.data?.work
  if (query.isSuccess && !view) return null
  return (
    <section id="work-life" className="home-panel work-panel" aria-labelledby="work-heading">
      <h2 id="work-heading">{panelTitle(name, 'work life')}</h2>
      <p className="subtle">Busy weeks, slow weeks, a project on the go and a raise once a year, as their job and city do them.{view && HOURS_TEXT[view.hours]} Picked for them; move a late night like anything on their calendar.</p>
      {query.isPending && <Loading label="Loading their work life" />}
      {query.isError && <ErrorNotice error={query.error} />}
      {view && <WorkDetails view={view} />}
    </section>
  )
}

function WorkDetails({ view }: { view: WorkLifeView }) {
  return <>
    <ul className="admin-state">{view.state.map((line) => <li key={line}>{line}</li>)}</ul>
    {view.level > 0 && view.status === 'working' && <WorkingOn view={view} />}
    {view.meter && <p className="subtle">{meterText(view.meter)}</p>}
    {view.late_nights.length > 0 && <><h3>Staying late</h3><AdminList items={view.late_nights} inWorkPanel /></>}
    {view.level > 0 && view.status === 'working' && <>
      <h3>Time off</h3>
      <p className="subtle">{timeOffText(view.vacation)}</p>
    </>}
    {view.events.length > 0 && <details className="wardrobe-group">
      <summary>What changed <span className="subtle">({view.events.length})</span></summary>
      <ul className="admin-state work-events">{view.events.map((event) => <li key={event.id}><span className="subtle">{eventDay(event)} · </span>{eventText(event)}</li>)}</ul>
    </details>}
  </>
}

/** What they're working on, in the user's words until it is due; then the app picks the next one as before. */
function WorkingOn({ view }: { view: WorkLifeView }) {
  const client = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState(view.project.title)
  const [notice, setNotice] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const save = async (next: string) => {
    try {
      client.setQueryData(WORK_KEY, await api<{ work: WorkLifeView | null }>('/life/work/project', { title: next }, 'PUT'))
      setNotice({ tone: 'info', text: next ? 'Saved. When it is due, the app picks what comes next.' : 'The app picked it again.' })
      setEditing(false)
    } catch (failure) { setNotice({ tone: 'error', text: failure instanceof Error ? failure.message : 'That was not saved.' }) }
  }
  const submit = (event: FormEvent) => { event.preventDefault(); void save(title.trim()) }
  const label = view.studying ? 'What they’re working on for class' : 'What they’re working on'
  return <>
    {editing
      ? <form className="rename-form home-add kid-form" onSubmit={submit} aria-label={label}>
        <div className="kid-field">
          <label htmlFor="work-project">{label}</label>
          <input id="work-project" value={title} maxLength={120} autoComplete="off" required onChange={(event) => setTitle(event.target.value)} />
        </div>
        <div className="rename-row kid-actions">
          <button type="submit" className="button primary">Save</button>
          <button type="button" className="button quiet" onClick={() => setEditing(false)}>Cancel</button>
        </div>
      </form>
      : <div className="person-actions">
        <button type="button" className="text-button" onClick={() => { setNotice(null); setTitle(view.project.title); setEditing(true) }}><Pencil aria-hidden="true" />Change what they’re working on</button>
        {view.own_project && <button type="button" className="text-button" onClick={() => void save('')}>Let the app pick</button>}
      </div>}
    <div aria-live="polite">{notice && <Notice tone={notice.tone}>{notice.text}</Notice>}</div>
  </>
}
