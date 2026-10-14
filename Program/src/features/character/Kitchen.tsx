import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, RotateCcw, ShoppingBasket } from 'lucide-react'
import { api } from '../../api'
import type { KitchenView } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { Field, Toggle } from '../../components/Fields'
import { AVOID_LABELS, DIET_LABELS, KITCHEN_KEY, WEEK_SHOWN, cuisineLine, favoritesLine, mealDay, mealLine, numbersLine, parseFavorites, skillLabel } from './kitchenText'
import { panelTitle } from './panelText'

type Feedback = { tone: 'info' | 'error'; text: string } | null

/** How the companion cooks and eats, their week of dinners and what is out at home: drawn by the app, changeable here. */
export function Kitchen({ name }: { name: string }) {
  const client = useQueryClient()
  const kitchen = useQuery({ queryKey: KITCHEN_KEY, queryFn: () => api<KitchenView>('/life/kitchen') })
  const [editing, setEditing] = useState(false)
  const [feedback, setFeedback] = useState<Feedback>(null)
  const save = async (body: object, done: string) => {
    try {
      client.setQueryData(KITCHEN_KEY, await api<KitchenView>('/life/kitchen', body, 'PATCH'))
      setFeedback({ tone: 'info', text: done })
      return true
    } catch (error) {
      setFeedback({ tone: 'error', text: error instanceof Error ? error.message : 'That change was not saved.' })
      return false
    }
  }
  const view = kitchen.data
  return (
    <section className="home-panel kitchen-panel" aria-labelledby="kitchen-heading">
      <h2 id="kitchen-heading">{panelTitle(name, 'kitchen')}</h2>
      <p className="subtle">How they cook and eat, from who they are and their city. Their dinners, grocery runs and what runs out happen on their own; change anything below and the days ahead follow.</p>
      <div aria-live="polite">{feedback && <Notice tone={feedback.tone}>{feedback.text}</Notice>}</div>
      {kitchen.isPending && <Loading label="Loading their kitchen" />}
      {kitchen.isError && <ErrorNotice error={kitchen.error} />}
      {view && <>
        <div className="kitchen-who">
          <p>{view.summary}</p>
          {favoritesLine(view.favorites) && <p>{favoritesLine(view.favorites)}</p>}
          <p className="subtle">{cuisineLine(view.cuisine)}</p>
        </div>
        {editing
          ? <KitchenForm view={view} save={save} onDone={() => setEditing(false)} />
          : <div className="person-actions">
            <button type="button" className="text-button" onClick={() => setEditing(true)}><Pencil aria-hidden="true" />Change how they eat</button>
            {view.changed.length > 0 && <button type="button" className="text-button" onClick={() => void save({ reset: true }, 'Back to their own way of eating.')}><RotateCcw aria-hidden="true" />Back to their own</button>}
          </div>}
        <Week view={view} />
        <div className="kitchen-pantry">
          <h3>At home</h3>
          <p>{view.pantry_text}</p>
          {numbersLine(view.numbers) && <p className="subtle">{numbersLine(view.numbers)}</p>}
        </div>
      </>}
    </section>
  )
}

type WeekDay = KitchenView['week'][number]

/** This week's dinners; past the first few rows, the older days fold under "Earlier this week". */
function Week({ view }: { view: KitchenView }) {
  const folded = view.week.length > WEEK_SHOWN ? view.week.slice(0, view.week.length - WEEK_SHOWN) : []
  const shown = view.week.slice(folded.length)
  const row = (day: WeekDay) => (
    <li key={day.date} className={day.today ? 'kitchen-today' : undefined}>
      <span className="kitchen-day">{mealDay(day, view.today)}</span>
      <span>{mealLine(day)}{day.groceries && <span className="badge kitchen-run"><ShoppingBasket aria-hidden="true" />{view.run_label}</span>}</span>
    </li>
  )
  return (
    <div className="kitchen-week">
      <h3>Dinners this week</h3>
      {folded.length > 0 && <details className="kitchen-earlier">
        <summary>Earlier this week</summary>
        <ul className="diary-list">{folded.map(row)}</ul>
      </details>}
      <ul className="diary-list">{shown.map(row)}</ul>
    </div>
  )
}

function KitchenForm({ view, save, onDone }: { view: KitchenView; save: (body: object, done: string) => Promise<boolean>; onDone: () => void }) {
  const [diet, setDiet] = useState(view.diet)
  const [avoids, setAvoids] = useState<string[]>(view.avoids)
  const [skill, setSkill] = useState(view.skill)
  const [bakes, setBakes] = useState(view.bakes)
  const [favorites, setFavorites] = useState(view.favorites.join(', '))
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const body = { diet, avoids, skill, bakes, favorites: parseFavorites(favorites) }
    if (await save(body, 'Saved. Their upcoming dinners follow it.')) onDone()
  }
  const flip = (name: string, on: boolean) => setAvoids(on ? [...avoids, name] : avoids.filter((item) => item !== name))
  return (
    <form className="form-stack kitchen-form" onSubmit={(event) => void submit(event)}>
      <Field label="Diet">{(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} value={diet} onChange={(event) => setDiet(event.target.value)}>
          {view.diets.map((item) => <option key={item} value={item}>{DIET_LABELS[item] ?? item}</option>)}
        </select>
      )}</Field>
      <fieldset className="kitchen-avoids">
        <legend>Avoids</legend>
        {view.avoid_choices.map((item) => (
          <Toggle key={item} label={AVOID_LABELS[item] ?? item} checked={avoids.includes(item)} onChange={(on) => flip(item, on)} />
        ))}
      </fieldset>
      <Field label="Cooking">{(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} value={skill} onChange={(event) => setSkill(Number(event.target.value))}>
          {view.skills.map((item, index) => <option key={item} value={index}>{skillLabel(item)}</option>)}
        </select>
      )}</Field>
      <Toggle label="Loves baking" checked={bakes} onChange={setBakes} />
      <Field label="Dishes they make a lot" hint="Separate dishes with commas. Up to five; they cook these more often.">{(id, describedBy) => (
        <input id={id} aria-describedby={describedBy} value={favorites} maxLength={300} onChange={(event) => setFavorites(event.target.value)} />
      )}</Field>
      <div className="form-actions">
        <button type="submit" className="button primary">Save</button>
        <button type="button" className="button" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}
