import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Eye, Moon, Sparkles } from 'lucide-react'
import type { View } from '../../companion'
import type { Observer, WatchDay, WatchFeed, WatchFocus, WatchLine } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { storyDate } from '../today/storyText'
import { BecomeThem } from '../today/BecomeThem'
import { reach } from '../notifications/useNotifications'
import { useObserver, useWatchActions, useWatchFeed } from './useObserver'
import { focusGroups, LINE_LABELS, lineTime, stepInLabel } from './watchText'

/**
 * Observer mode (companion/observer.py): just watch the world go on. The page follows one person, the focus, and
 * tells their last week the way a narrator would (companion/life/narrator.py), in real time.
 */
export function Watch({ go }: { go: (view: View) => void }) {
  const observer = useObserver()
  const [error, setError] = useState('')
  const { change } = useWatchActions()
  const run = async (body: { watching?: boolean; focus?: string }) => {
    setError('')
    try { return await change(body) } catch (failure) { setError(failure instanceof Error ? failure.message : 'That did not work. Try again.'); return null }
  }
  if (observer.isPending) return <Loading label="Opening the world" />
  if (observer.isError) return <ErrorNotice error={observer.error} />
  const data = observer.data
  if (!data.focus) return <Notice>There is nobody here to watch yet.</Notice>
  return (
    <section className="page watch" aria-labelledby="watch-heading">
      <WatchHeader data={data} focus={data.focus} onChange={run} go={go} />
      {error && <Notice tone="error">{error}</Notice>}
      {data.watching ? <Days focus={data.focus} /> : <NotWatching onStart={() => void run({ watching: true })} />}
    </section>
  )
}

interface HeaderProps { data: Observer; focus: WatchFocus; onChange: (body: { watching?: boolean; focus?: string }) => Promise<Observer | null>; go: (view: View) => void }

function WatchHeader({ data, focus, onChange, go }: HeaderProps) {
  return (
    <header className="page-header watch-header">
      <div className="watch-title">
        <p className="eyebrow">{data.watching ? 'Just watching' : 'Watch'}</p>
        <h1 id="watch-heading">{focus.name}</h1>
        <p className="subtle">{focus.line}</p>
      </div>
      <div className="watch-controls">
        <FocusPicker data={data} focus={focus} onPick={(key) => void onChange({ focus: key })} />
        {data.watching && <div className="watch-buttons">
          <StepIn focus={focus} onStop={() => onChange({ watching: false })} go={go} />
          <button type="button" className="text-button" onClick={() => void onChange({ watching: false })}>Stop watching</button>
        </div>}
      </div>
    </header>
  )
}

/** Who to follow: the app picks first; anyone here can be followed instead. */
function FocusPicker({ data, focus, onPick }: { data: Observer; focus: WatchFocus; onPick: (key: string) => void }) {
  return (
    <label className="watch-picker">
      <span className="field-label">Following</span>
      <select value={focus.key} onChange={(event) => onPick(event.target.value)}>
        {focusGroups(data.choices).map((group) => (
          <optgroup key={group.label} label={group.label}>
            {group.people.map((person) => <option key={person.key} value={person.key}>{person.name}</option>)}
          </optgroup>
        ))}
      </select>
    </label>
  )
}

/** Step back in: a chat with a companion, or a new life as the townsperson being watched. */
function StepIn({ focus, onStop, go }: { focus: WatchFocus; onStop: () => Promise<Observer | null>; go: (view: View) => void }) {
  const client = useQueryClient()
  if (focus.kind === 'townsperson') return <BecomeThem person={{ key: focus.key, name: focus.name }} />
  const talk = async () => {
    if (await onStop()) await reach(client, go, 'conversation', focus.companion_id)
  }
  return <button type="button" className="button primary" onClick={() => void talk()}>{stepInLabel(focus)}</button>
}

function NotWatching({ onStart }: { onStart: () => void }) {
  return (
    <div className="watch-start">
      <p>Sit back and watch this world go on without you. Nobody texts you or asks you along while you watch, and everyone&apos;s days carry on at their usual pace. Writing to anyone steps you back in.</p>
      <button type="button" className="button primary" onClick={onStart}><Eye aria-hidden="true" />Just watch</button>
    </div>
  )
}

function Days({ focus }: { focus: WatchFocus }) {
  const feed = useWatchFeed(focus.key)
  if (feed.isPending) return <Loading label={`Catching up on ${focus.name}`} />
  if (feed.isError) return <ErrorNotice error={feed.error} />
  if (!feed.data.days.length) return <p className="subtle watch-empty">Nothing yet. Their day is only just starting.</p>
  return (
    <div className="watch-days">
      {feed.data.days.map((day) => <Day key={day.date} day={day} feed={feed.data} />)}
    </div>
  )
}

function Day({ day, feed }: { day: WatchDay; feed: WatchFeed }) {
  const heading = `watch-day-${day.date}`
  return (
    <section className="watch-day" aria-labelledby={heading}>
      <h2 id={heading}>{storyDate(day.date)}</h2>
      {day.entry && <p className="watch-entry">{day.entry}</p>}
      <ol className="watch-lines">
        {day.items.map((line) => <Line key={line.id} line={line} timezone={feed.timezone} />)}
      </ol>
    </section>
  )
}

function Line({ line, timezone }: { line: WatchLine; timezone: string }) {
  const label = LINE_LABELS[line.kind]
  const Icon = line.kind === 'dream' ? Moon : line.kind === 'thought' ? Sparkles : null
  return (
    <li className={`watch-line watch-${line.kind}`}>
      <time dateTime={line.at}>{lineTime(line, timezone)}</time>
      <div className="watch-line-body">
        <p>{Icon && <Icon aria-hidden="true" />}{label && <span className="visually-hidden">{label}: </span>}{line.text}</p>
        {line.inner && <p className="watch-inner">{line.inner}</p>}
        {line.numbers.length > 0 && <p className="watch-numbers">{line.numbers.map((number) => <span key={number} className="badge">{number}</span>)}</p>}
      </div>
    </li>
  )
}
