import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { BookHeart, Check, Lock, Map as MapIcon, Network, Newspaper, Play, RotateCcw, X } from 'lucide-react'
import { api } from '../../api'
import { SETTINGS_KEY, type View } from '../../companion'
import type { Companion, LifeEvent, PauseRecord, ScrapbookListing, Today as TodayData } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { Circle } from './Circle'
import { CorrectEvent, type EventCorrection } from './CorrectEvent'
import { EventItem } from './EventItem'
import { MoneyPanel } from './MoneyPanel'
import { NowCard } from './NowCard'
import { RowGroup } from '../../components/Rows'
import { InfoTip } from '../../components/InfoTip'
import { OurFamily } from './OurFamily'
import { Paper } from './Paper'
import { TalkOfTheTown } from './TalkOfTheTown'
import { Recommendations } from './Recommendations'
import { Chapters } from './Chapters'
import { Reactions } from './Reactions'
import { Storylines } from './Storylines'
import { Townsfolk } from './Townsfolk'
import { OnTheirMind } from './OnTheirMind'
import { OutTogether, Trips } from './OutTogether'
import { AwayNowAction, AwayRows } from './AwayTogether'
import { useAwayTrips } from './useTogether'
import { awayNowLine, type Trip } from './outingText'
import { AdminList, FOLD } from './AdminList'
import { LittleThings } from './LittleThings'
import { WordGetsAround } from './WordGetsAround'
import { headerOccasions } from './storyText'
import { bodyText, moodText, pauseToFill } from './todayText'
import { SCRAPBOOKS_KEY, featuredCard } from '../year/yearText'
import { askForNew } from '../feed/feedState'
import { firstName } from '../character/panelText'

const TODAY_KEY = ['today']

export function Today({ companion, go }: { companion: Companion; go: (view: View) => void }) {
  const client = useQueryClient()
  const today = useQuery({ queryKey: TODAY_KEY, queryFn: () => api<TodayData>('/today') })
  const away = useAwayTrips()
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
      <header className="today-head">
        <h1>Today</h1>
        {data.feed_unread > 0 && <button type="button" className="button" onClick={() => { askForNew(); go('posts') }}><Newspaper aria-hidden="true" />{data.feed_unread} new in Feed</button>}
        <span className="today-tools">
          <button type="button" className="icon-button" aria-label="Map" title="Map" onClick={() => go('map')}><MapIcon aria-hidden="true" /></button>
          <button type="button" className="icon-button" aria-label="Who knows who" title="Who knows who" onClick={() => go('people')}><Network aria-hidden="true" /></button>
          <button type="button" className="icon-button" aria-label="Secrets" title="Secrets" onClick={() => go('secrets')}><Lock aria-hidden="true" /></button>
        </span>
      </header>
      <NowCard data={data} name={name} go={go} status={awayNowLine(away.now)}>
        <AwayNowAction trip={away.now} />
        <Feeling data={data} name={name} />
        {data.mind && <OnTheirMind thoughts={data.mind.thoughts} name={name} />}
      </NowCard>
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
      <Section id="changes" title={data.last_seen_at ? 'Since you were last here' : 'Recently'}>
        {data.changes.map((event) => (
          <EventItem key={event.id} event={event}>
            {event.status === 'committed' && <CorrectEvent event={event} onSave={(correction) => correct(event, correction)} />}
          </EventItem>
        ))}
      </Section>
      <OutTogether name={name} />
      <Plans data={data} name={name} go={go} away={away.coming} />
      <Trips name={name} />
      <Recommendations name={name} />
      <Chapters name={name} />
      <WordGetsAround name={name} />
      <Storylines name={name} />
      <LittleThings moments={data.moments} dreams={data.dreams} name={name} />
      <Reactions name={name} />
      <OurFamily family={data.family} />
      <RowGroup className="today-folds"><MoneyPanel name={name} go={() => go('character')} /></RowGroup>
      <Circle name={name} />
      <Paper />
      <TalkOfTheTown name={name} />
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
    {headerOccasions(occasions, name).map((item) => <p key={item.key} className="subtle">{item.text}</p>)}
  </>
}

/** The occasions for the header; while the scrapbook card shows, it carries the anniversary instead. */
function useOccasions(data: TodayData, name: string) {
  const listing = useQuery({ queryKey: SCRAPBOOKS_KEY, queryFn: () => api<ScrapbookListing>('/life/year') })
  const card = featuredCard(listing.data, name)
  return (data.occasions ?? []).filter((item) => !(card && item.kind === 'anniversary'))
}

/** A list of events under a heading; an empty one is left out (style guide: empty sections hidden). The hint sits
 * behind an InfoTip. */
function Section({ id, title, hint, children }: { id: string; title: string; hint?: string; children: ReactNode[] }) {
  if (!children.length) return null
  return (
    <section className="today-section" aria-labelledby={`${id}-heading`}>
      <div className="today-section-title"><h2 id={`${id}-heading`}>{title}</h2>{hint && <InfoTip id={`${id}-about`} label={title} text={hint} />}</div>
      <ul className="event-list">{children}</ul>
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

function Plans({ data, name, go, away }: { data: TodayData; name: string; go: (view: View) => void; away: Trip[] }) {
  const { shared, companion, threads } = data.plans
  const admin = data.plans.admin ?? []
  const stays = data.plans.stays ?? []
  const groups = [shared, away, companion, threads, admin, stays].filter((list) => list.length).length
  if (!groups) return null
  // One group needs no heading of its own (Iris): "Coming up" says it, and All errands sits beside that heading.
  const many = groups > 1
  const allErrands = admin.length > 0 && <button type="button" className="text-button today-more" onClick={() => go('character')}>All errands</button>
  return (
    <section className="today-section" aria-labelledby="plans-heading">
      <div className="today-section-title"><h2 id="plans-heading">Coming up</h2>{!many && allErrands}</div>
      <PlanGroup title="Yours" many={many} count={shared.length}>
        <ul className="plain-list">{shared.map((plan) => <li key={plan.id}><strong>{plan.subject}</strong>: {plan.value} <span className="badge">{plan.status}</span></li>)}</ul>
      </PlanGroup>
      <PlanGroup title="Away together" many={many} count={away.length}><AwayRows trips={away} name={name} /></PlanGroup>
      <PlanGroup title={`${firstName(name)}'s`} many={many} count={companion.length}>
        <ul className="event-list">{companion.map((event) => <EventItem key={event.id} event={event} />)}</ul>
      </PlanGroup>
      <PlanGroup title="Stays with the other parent" many={many} count={stays.length}><AdminList items={stays} /></PlanGroup>
      <PlanGroup title="Errands and appointments" many={many} count={admin.length} extra={allErrands}><AdminList items={admin.slice(0, FOLD)} fold={null} /></PlanGroup>
      <PlanGroup title="Still unresolved" many={many} count={threads.length}>
        <ul className="event-list">{threads.map((event) => <EventItem key={event.id} event={event} />)}</ul>
      </PlanGroup>
    </section>
  )
}

/** One group under Coming up, with its own heading only while there is more than one group. */
function PlanGroup({ title, many, count, extra, children }: { title: string; many: boolean; count: number; extra?: ReactNode; children: ReactNode }) {
  if (!count) return null
  return <>
    {many && <div className="today-group-title"><h3>{title}</h3>{extra}</div>}
    {children}
  </>
}
