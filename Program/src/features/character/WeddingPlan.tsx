import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Map as MapIcon, MapPin } from 'lucide-react'
import { api } from '../../api'
import type { AdminView, WeddingGuest, WeddingPlan as Plan } from '../../types'
import { Field } from '../../components/Fields'
import { Notice } from '../../components/Feedback'
import { ADMIN_KEY } from '../today/adminText'
import { dayText, timeText, TOGETHER_KEY } from '../today/outingText'
import { WhyItWent } from '../today/WhyItWent'
import { firstName } from './panelText'
import { budgetLine, guestCount, planLine, takeOpening, taskLine, tomorrow } from './weddingText'

export interface WeddingChange { day?: string; venue?: boolean; size?: string; guest?: string; invited?: boolean }

/** The wedding card in "You and them" on the Character page, under the steps, while one is being planned. Today's
 * "Change the plan" link scrolls to it. */
export function Wedding({ name }: { name: string }) {
  const admin = useQuery({ queryKey: ADMIN_KEY, queryFn: () => api<AdminView>('/life/admin') })
  const box = useRef<HTMLDivElement>(null)
  const plan = admin.data?.wedding?.status === 'planned' ? admin.data.wedding : null
  useEffect(() => { if (plan && takeOpening()) box.current?.scrollIntoView?.({ block: 'start' }) }, [plan])
  if (!plan) return null
  return <div ref={box} id="wedding"><WeddingPlan plan={plan} name={name} /></div>
}

/** The wedding an engagement plans (companion/life/wedding.py): picked by the app from their city's customs, their
 * pay and their people; the user moves the day, sends it somewhere else, changes the size or leaves a guest off.
 * Every change saves at once. */
export function WeddingPlan({ plan, name }: { plan: Plan; name: string }) {
  const client = useQueryClient()
  const [error, setError] = useState('')
  const who = firstName(name)
  const save = async (change: WeddingChange) => {
    setError('')
    try {
      client.setQueryData(ADMIN_KEY, await api<AdminView>('/life/admin/wedding', change, 'PUT'))
      void client.invalidateQueries({ queryKey: TOGETHER_KEY })
      void client.invalidateQueries({ queryKey: ['today'] })
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'That was not saved.') }
  }
  const theirs = plan.guests.filter((guest) => guest.side === 'theirs')
  const yours = plan.guests.filter((guest) => guest.side === 'yours')
  return (
    <section className="wedding-plan" aria-labelledby="wedding-heading">
      <h3 id="wedding-heading">Your wedding</h3>
      <p className="wedding-line">{planLine(plan)}</p>
      <p className="subtle">{plan.customs.charAt(0).toUpperCase() + plan.customs.slice(1)}.</p>
      {budgetLine(plan, who) && <p className="subtle">{budgetLine(plan, who)}</p>}
      <div className="wedding-fields">
        <Field label="The day" hint={plan.moved_by_user ? 'You picked this day.' : `Picked by the app, the way weddings go in ${who}'s city.`}>
          {(id, describedBy) => <input id={id} type="date" aria-describedby={describedBy} value={plan.date} min={tomorrow()}
            onChange={(event) => { if (event.target.value) void save({ day: event.target.value }) }} />}
        </Field>
        <div>
          <Field label="How big" hint={guestCount(plan)}>
            {(id, describedBy) => <select id={id} aria-describedby={describedBy} value={plan.size} onChange={(event) => void save({ size: event.target.value })}>
              {plan.sizes.map((size) => <option key={size.key} value={size.key}>{size.label}</option>)}
            </select>}
          </Field>
          {plan.consequence_id && <WhyItWent id={plan.consequence_id} />}
        </div>
      </div>
      <Venue plan={plan} save={save} />
      {plan.guests.length > 0 && <details className="wardrobe-group">
        <summary>Guest list <span className="subtle">({plan.guests.filter((guest) => guest.invited).length} named)</span></summary>
        {theirs.length > 0 && <Guests title={`${who}'s side`} guests={theirs} save={save} />}
        {yours.length > 0 && <Guests title="Your side" guests={yours} save={save} />}
      </details>}
      <Tasks tasks={plan.tasks} />
      {error && <Notice tone="error">{error}</Notice>}
    </section>
  )
}

function Venue({ plan, save }: { plan: Plan; save: (change: WeddingChange) => Promise<void> }) {
  const { venue } = plan
  return (
    <p className="wedding-venue">
      <span>{venue.name}{venue.neighborhood && <span className="subtle">, {venue.neighborhood}</span>} · {timeText(plan.at)} to {timeText(plan.until)}</span>
      {venue.mapped && <span className="wedding-venue-actions">
        <a className="text-button" href={`#map/${encodeURIComponent(venue.id)}`}><MapIcon aria-hidden="true" />Show on map</a>
        <button type="button" className="text-button" onClick={() => void save({ venue: true })}><MapPin aria-hidden="true" />Somewhere else</button>
      </span>}
    </p>
  )
}

function Tasks({ tasks }: { tasks: Plan['tasks'] }) {
  if (!tasks.length) return null
  if (tasks.length === 1) return <p className="subtle">{taskLine(tasks[0], dayText)}</p>
  return (
    <details className="wardrobe-group">
      <summary>Planning <span className="subtle">({tasks.filter((task) => task.done).length} of {tasks.length} done)</span></summary>
      <ul className="wedding-tasks">
        {tasks.map((task) => <li key={`${task.title}-${task.date}`} className={task.done ? 'done' : undefined}><span>{task.title}</span> <span className="subtle">{dayText(task.date)}</span></li>)}
      </ul>
    </details>
  )
}

function Guests({ title, guests, save }: { title: string; guests: WeddingGuest[]; save: (change: WeddingChange) => Promise<void> }) {
  return (
    <fieldset className="wedding-guests">
      <legend>{title}</legend>
      {guests.map((guest) => (
        <label key={guest.key} className="check-row">
          <input type="checkbox" checked={guest.invited} onChange={(event) => void save({ guest: guest.key, invited: event.target.checked })} />
          <span>{guest.name || guest.who}{guest.name && <span className="subtle"> · {guest.who}</span>}</span>
        </label>
      ))}
    </fieldset>
  )
}
