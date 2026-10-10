import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { BookHeart, Check, Map as MapIcon, Network, Newspaper, Play, RotateCcw, X } from 'lucide-react'
import { api } from '../../api'
import { SETTINGS_KEY, type View } from '../../companion'
import type { Companion, LifeEvent, PauseRecord, ScrapbookListing, Today as TodayData } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { Circle } from './Circle'
import { CorrectEvent, type EventCorrection } from './CorrectEvent'
import { EventItem } from './EventItem'
import { MoneyPanel } from './MoneyPanel'
import { Paper } from './Paper'
import { Recommendations } from './Recommendations'
import { Chapters } from './Chapters'
import { Reactions } from './Reactions'
import { Storylines } from './Storylines'
import { Townsfolk } from './Townsfolk'
import { OnTheirMind } from './OnTheirMind'
import { LittleThings } from './LittleThings'
import { WordGetsAround } from './WordGetsAround'
import { occasionText } from './storyText'
import { bodyText, changesEmpty, moodText, pauseToFill } from './todayText'
import { SCRAPBOOKS_KEY, featuredCard } from '../year/yearText'

const TODAY_KEY = ['today']

export function Today({ companion, go }: { companion: Companion; go: (view: View) => void }) {
  const client = useQueryClient()
  const today = useQuery({ queryKey: TODAY_KEY, queryFn: () => api<TodayData>('/today') })
  const [feedback, setFeedback] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const seen = useRef(false)
  const name = companion.version.name

  // The user has looked at Today once it has loaded; the next visit's changes start from here.
  useEffect(() => {
    if (today.isSuccess && !seen.current) { seen.current = true; void api('/today/seen', {}).catch(() => undefined) }
  }, [today.isSuccess])

  const act = async (action: () => Promise<unknown>, done: string) => {
    try {
      await action()
      setFeedback({ tone: 'info', text: done })
    } catch (error) { setFeedback({ tone: 'error', text: error instanceof Error ? error.message : 'That did not work.' }) }
    void client.invalidateQueries({ queryKey: TODAY_KEY })
  }
  const decide = (event: LifeEvent, keep: boolean) => act(async () => {
    const result = await api<LifeEvent>(`/events/${event.id}/${keep ? 'commit' : 'reject'}`, {})
    if (keep && result.status === 'rejected') throw new Error(`That event could not be kept: ${result.rejection ?? 'it is out of date'}.`)
    void client.invalidateQueries({ queryKey: ['feed'] })
  }, keep ? `Kept. It is now part of ${name}'s life.` : 'Discarded. It will not be mentioned.')
  const resume = () => act(async () => { client.setQueryData(SETTINGS_KEY, await api('/resume', {})) }, `Resumed. ${name}'s life picks up from now.`)
  const correct = async (event: LifeEvent, correction: EventCorrection) => {
    let saved = false
    await act(async () => {
      await api(`/events/${event.id}/correct`, correction)
      saved = true
      void client.invalidateQueries({ queryKey: ['feed'] })
    }, 'Corrected. The earlier version is kept.')
    return saved
  }
  const resetMood = (id: string) => act(() => api(`/today/mood/${id}/reset`, {}), 'Mood reset.')

  if (today.isPending) return <Loading label="Loading today" />
  if (today.isError) return <section className="page"><ErrorNotice error={today.error} /></section>
  const data = today.data
  return (
    <section className="page today">
      <header className="page-header">
        <div>
          <h1>{name}'s day</h1>
          <p className="subtle">Message {name} any time. When they are busy or asleep, they answer when they can.</p>
          <Feeling data={data} name={name} />
          {data.mind && <OnTheirMind thoughts={data.mind.thoughts} name={name} />}
        </div>
        <div className="today-actions">
          {data.feed_unread > 0 && <button type="button" className="button" onClick={() => go('feed')}><Newspaper aria-hidden="true" />{data.feed_unread} new in Feed</button>}
          <button type="button" className="button" onClick={() => go('map')}><MapIcon aria-hidden="true" />Map</button>
          <button type="button" className="button" onClick={() => go('people')}><Network aria-hidden="true" />Who knows who</button>
        </div>
      </header>
      <div aria-live="polite">{feedback && <Notice tone={feedback.tone}>{feedback.text}</Notice>}</div>
      <StateNotices data={data} name={name} onResume={resume} />
      <YearReady name={name} go={go} />
      {data.paused ? null : <PausedTime name={name} onDone={(text) => { setFeedback({ tone: 'info', text }); void client.invalidateQueries({ queryKey: TODAY_KEY }) }} />}
      {data.mood && (
        <section className="today-section" aria-labelledby="mood-heading">
          <h2 id="mood-heading">Mood</h2>
          <Notice action={<button type="button" className="text-button" onClick={() => void resetMood(data.mood!.id)}><RotateCcw aria-hidden="true" />Reset</button>}>{moodText(data.mood, name)}</Notice>
        </section>
      )}
      {data.review.length > 0 && (
        <Section id="review" title="Waiting for you" hint={`Things that could have happened in ${name}'s life. Keep the ones you like; discarded ones are never mentioned.`}>
          {data.review.map((event) => (
            <EventItem key={event.id} event={event}>
              <div className="form-actions">
                <button type="button" className="button" onClick={() => void decide(event, true)}><Check aria-hidden="true" />Keep</button>
                <button type="button" className="button quiet" onClick={() => void decide(event, false)}><X aria-hidden="true" />Discard</button>
              </div>
            </EventItem>
          ))}
        </Section>
      )}
      <Section id="changes" title={data.last_seen_at ? 'Since you were last here' : 'Recently'} empty={changesEmpty(name, data.review.length)}>
        {data.changes.map((event) => (
          <EventItem key={event.id} event={event}>
            {event.status === 'committed' && <CorrectEvent event={event} onSave={(correction) => correct(event, correction)} />}
          </EventItem>
        ))}
      </Section>
      <Plans data={data} name={name} />
      <Recommendations name={name} />
      <Chapters name={name} />
      <WordGetsAround name={name} />
      <Storylines name={name} />
      <LittleThings moments={data.moments} dreams={data.dreams} name={name} />
      <Reactions name={name} />
      <Routine data={data} name={name} go={go} />
      <MoneyPanel name={name} go={() => go('character')} />
      <Circle name={name} />
      <Paper />
      <Townsfolk name={name} go={go} />
    </section>
  )
}

function Feeling({ data, name }: { data: TodayData; name: string }) {
  const text = bodyText(data.day?.body, name)
  const occasions = useOccasions(data, name)
  return <>
    {text && <p className="subtle">{text}</p>}
    {data.feeling && data.feeling.feeling !== 'calm' && <p className="subtle">{data.feeling.text}{data.feeling.reason ? `: ${data.feeling.reason}` : ''}.</p>}
    {occasions.map((item) => <p key={item.key} className="subtle">{occasionText(item, name)}</p>)}
  </>
}

/** The occasions for the header; while the scrapbook card shows, it carries the anniversary instead. */
function useOccasions(data: TodayData, name: string) {
  const listing = useQuery({ queryKey: SCRAPBOOKS_KEY, queryFn: () => api<ScrapbookListing>('/life/year') })
  const card = featuredCard(listing.data, name)
  return (data.occasions ?? []).filter((item) => !(card && item.kind === 'anniversary'))
}

function Section({ id, title, hint, empty, children }: { id: string; title: string; hint?: string; empty?: string; children: ReactNode[] }) {
  return (
    <section className="today-section" aria-labelledby={`${id}-heading`}>
      <h2 id={`${id}-heading`}>{title}</h2>
      {hint && <p className="subtle">{hint}</p>}
      {children.length ? <ul className="event-list">{children}</ul> : empty && <p className="subtle">{empty}</p>}
    </section>
  )
}

/** On an anniversary of the first talk, and in the first week of January, the scrapbook of the year just finished. */
/** In an anniversary week or January's first week, a small scrapbook card. Opening it or putting it away keeps it
 * away for good. */
function YearReady({ name, go }: { name: string; go: (view: View) => void }) {
  const client = useQueryClient()
  const listing = useQuery({ queryKey: SCRAPBOOKS_KEY, queryFn: () => api<ScrapbookListing>('/life/year') })
  const card = featuredCard(listing.data, name)
  if (!card) return null
  const dismiss = async () => client.setQueryData(SCRAPBOOKS_KEY, await api<ScrapbookListing>(`/life/year/${card.key}/seen`, {}))
  return (
    <section className="year-card" aria-labelledby="year-card-heading">
      <h2 id="year-card-heading">{card.title}</h2>
      <p>{card.stat}</p>
      <button type="button" className="button primary" onClick={() => go('year')}><BookHeart aria-hidden="true" />Open the scrapbook</button>
      <button type="button" className="icon-button year-card-close" aria-label="Put the scrapbook away" onClick={() => void dismiss()}><X aria-hidden="true" /></button>
    </section>
  )
}

function StateNotices({ data, name, onResume }: { data: TodayData; name: string; onResume: () => void }) {
  return <>
    {data.paused && <Notice action={<button type="button" className="text-button" onClick={onResume}><Play aria-hidden="true" />Resume</button>}>Paused since {new Date(data.paused_at!).toLocaleString()}. Nothing happens in {name}'s life while paused.</Notice>}
    {data.clock_behind && <Notice>Your computer's clock is earlier than time already lived through here, so nothing new is added until it catches up.</Notice>}
    {data.last_run?.status === 'failed' && <Notice tone="error">The last catch-up failed: {data.last_run.error ?? 'unknown error'}. It will be tried again next time you open the app.</Notice>}
    {data.last_run?.status === 'interrupted' && <Notice>The last catch-up was interrupted and will finish next time.</Notice>}
  </>
}

function PausedTime({ name, onDone }: { name: string; onDone: (text: string) => void }) {
  const pauses = useQuery({ queryKey: ['pauses'], queryFn: () => api<PauseRecord[]>('/life/pauses') })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pause = pauseToFill(pauses.data ?? [])
  if (!pause) return null
  const fill = async () => {
    setBusy(true)
    try {
      await api(`/life/pauses/${pause.id}/catch-up`, {})
      void pauses.refetch()
      onDone(`Filled in the paused time with a few moments from ${name}'s routine.`)
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'That did not work.') } finally { setBusy(false) }
  }
  return (
    <Notice action={<button type="button" className="text-button" disabled={busy} onClick={() => void fill()}>Fill it in</button>}>
      {error ?? `The time you paused (${new Date(pause.started_at).toLocaleDateString()}) was skipped. You can fill it in with a few ordinary moments, once.`}
    </Notice>
  )
}

function Plans({ data, name }: { data: TodayData; name: string }) {
  const { shared, companion, threads } = data.plans
  if (!shared.length && !companion.length && !threads.length) return null
  return (
    <section className="today-section" aria-labelledby="plans-heading">
      <h2 id="plans-heading">Plans</h2>
      {shared.length > 0 && <>
        <h3>Yours</h3>
        <ul className="plain-list">{shared.map((plan) => <li key={plan.id}><strong>{plan.subject}</strong>: {plan.value} <span className="badge">{plan.status}</span></li>)}</ul>
      </>}
      {companion.length > 0 && <><h3>{name}'s</h3><ul className="event-list">{companion.map((event) => <EventItem key={event.id} event={event} />)}</ul></>}
      {threads.length > 0 && <><h3>Still unresolved</h3><ul className="event-list">{threads.map((event) => <EventItem key={event.id} event={event} />)}</ul></>}
    </section>
  )
}

function Routine({ data, name, go }: { data: TodayData; name: string; go: (view: View) => void }) {
  const { current, next, default_schedule } = data.routine
  const at = (value: string) => new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit', timeZone: data.companion_timezone }).format(new Date(value))
  return (
    <section className="today-section" aria-labelledby="routine-heading">
      <h2 id="routine-heading">Routine</h2>
      <ul className="plain-list">
        {current && <li>Now: {current.block.label}, until {at(current.ends_at)} their time</li>}
        {next && <li>Next: {next.block.label}, from {at(next.starts_at)} their time</li>}
      </ul>
      {default_schedule && <p className="subtle">{name} is following a gentle default day. <button type="button" className="text-button inline" onClick={() => go('character')}>Describe their routine</button></p>}
    </section>
  )
}
