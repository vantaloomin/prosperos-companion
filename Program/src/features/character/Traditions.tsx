import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Plus, RotateCcw, Trash2 } from 'lucide-react'
import { api } from '../../api'
import type { Tradition, TraditionsView } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { Toggle } from '../../components/Fields'
import { decorationsText, nextText } from './traditionsText'

const TRADITIONS_KEY = ['traditions']
const TEXT_LIMIT = 400

type Act = (action: () => Promise<TraditionsView>, done: string) => Promise<boolean>

/** The holidays their family keeps, drawn from their city's calendar and their circle, and what is up at home for the
 * season. The app decides them; the user can reword one, drop it, bring it back or add their own. */
export function Traditions({ name }: { name: string }) {
  const client = useQueryClient()
  const [feedback, setFeedback] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const view = useQuery({ queryKey: TRADITIONS_KEY, queryFn: () => api<TraditionsView>('/life/traditions') })
  const act: Act = async (action, done) => {
    try {
      client.setQueryData(TRADITIONS_KEY, await action())
      setFeedback({ tone: 'info', text: done })
      void client.invalidateQueries({ queryKey: ['today'] })
      return true
    } catch (error) {
      setFeedback({ tone: 'error', text: error instanceof Error ? error.message : 'That change was not saved.' })
      return false
    }
  }
  return (
    <section className="home-panel traditions-panel" aria-labelledby="traditions-heading">
      <h2 id="traditions-heading">{name}'s family traditions</h2>
      <p className="subtle">The holidays their family keeps, from their city's calendar and the people in their life. They come up in chat the week before, and the day itself goes to them.</p>
      <div aria-live="polite">{feedback && <Notice tone={feedback.tone}>{feedback.text}</Notice>}</div>
      {view.isPending && <Loading label="Loading their traditions" />}
      {view.isError && <ErrorNotice error={view.error} />}
      {view.data && <TraditionList data={view.data} act={act} />}
    </section>
  )
}

function TraditionList({ data, act }: { data: TraditionsView; act: Act }) {
  const [removed, setRemoved] = useState(false)
  const [adding, setAdding] = useState(false)
  return <>
    {data.decorations.length > 0 && <p className="subtle">{decorationsText(data.decorations)}</p>}
    {data.traditions.length === 0 && <p className="subtle">No traditions yet. Their city's calendar has no family holidays in it, or you dropped them all.</p>}
    <ul className="person-list">{data.traditions.map((item) => <TraditionCard key={item.id} item={item} act={act} />)}</ul>
    {adding
      ? <AddForm view={data} act={act} onDone={() => setAdding(false)} />
      : data.holidays.length > 0 && <button type="button" className="button" onClick={() => setAdding(true)}><Plus aria-hidden="true" />Add a tradition</button>}
    {data.removed.length > 0 && <Toggle label="Show traditions you dropped" checked={removed} onChange={setRemoved} />}
    {removed && <ul className="person-list">{data.removed.map((item) => <TraditionCard key={item.id} item={item} act={act} gone />)}</ul>}
  </>
}

function TraditionCard({ item, act, gone = false }: { item: Tradition; act: Act; gone?: boolean }) {
  const [editing, setEditing] = useState(false)
  const remove = () => act(() => api(`/life/traditions/${item.id}/remove`, {}), `${item.name} is no longer a tradition.`)
  const restore = () => act(() => api(`/life/traditions/${item.id}/restore`, {}), `${item.name} is back.`)
  const next = nextText(item.next)
  return (
    <li className={`person-card${gone ? ' removed' : ''}`}>
      <header>
        {next && <p className="subtle">{next}</p>}
        <h3>{item.name}</h3>
      </header>
      {editing
        ? <EditForm item={item} act={act} onDone={() => setEditing(false)} />
        : <>
          <p>{item.text}</p>
          {item.origin === 'user' ? <p className="subtle">Added by you</p> : item.edited && <p className="subtle">Edited by you</p>}
          <div className="person-actions">
            {gone
              ? <button type="button" className="text-button" onClick={() => void restore()}><RotateCcw aria-hidden="true" />Restore</button>
              : <>
                <button type="button" className="text-button" onClick={() => setEditing(true)}><Pencil aria-hidden="true" />Edit</button>
                <button type="button" className="text-button" onClick={() => void remove()}><Trash2 aria-hidden="true" />Drop</button>
              </>}
          </div>
        </>}
    </li>
  )
}

function EditForm({ item, act, onDone }: { item: Tradition; act: Act; onDone: () => void }) {
  const [text, setText] = useState(item.text)
  const save = async (event: FormEvent) => {
    event.preventDefault()
    if (!text.trim()) return
    if (await act(() => api(`/life/traditions/${item.id}`, { text: text.trim() }, 'PATCH'), `Saved. ${item.name} goes this way from now on.`)) onDone()
  }
  return (
    <form className="rename-form" onSubmit={(event) => void save(event)}>
      <label htmlFor={`tradition-${item.id}`}>How they keep it</label>
      <textarea id={`tradition-${item.id}`} rows={3} value={text} maxLength={TEXT_LIMIT} onChange={(event) => setText(event.target.value)} />
      <div className="rename-row">
        <button type="submit" className="button primary" disabled={!text.trim()}>Save</button>
        <button type="button" className="button quiet" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}

function AddForm({ view, act, onDone }: { view: TraditionsView; act: Act; onDone: () => void }) {
  const [holiday, setHoliday] = useState(view.holidays[0]?.id ?? '')
  const [text, setText] = useState('')
  const chosen = view.holidays.find((item) => item.id === holiday)
  const save = async (event: FormEvent) => {
    event.preventDefault()
    if (!text.trim() || !chosen) return
    if (await act(() => api('/life/traditions', { holiday, text: text.trim() }), `Added a tradition for ${chosen.name}.`)) onDone()
  }
  return (
    <form className="rename-form" onSubmit={(event) => void save(event)}>
      <label htmlFor="tradition-add-holiday">Holiday</label>
      <select id="tradition-add-holiday" value={holiday} onChange={(event) => setHoliday(event.target.value)}>
        {view.holidays.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
      </select>
      <label htmlFor="tradition-add-text">How they keep it</label>
      <textarea id="tradition-add-text" rows={3} value={text} maxLength={TEXT_LIMIT} required placeholder="Such as: a long walk on the beach, then pie at their sister's." onChange={(event) => setText(event.target.value)} />
      <div className="rename-row">
        <button type="submit" className="button primary" disabled={!text.trim()}>Add</button>
        <button type="button" className="button quiet" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}
