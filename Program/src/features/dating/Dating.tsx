import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Heart, MapPin, X } from 'lucide-react'
import { api } from '../../api'
import type { View } from '../../companion'
import type { CitySummary, Dating as DatingData, DatingCard, DatingMatch, DatingProfile } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { useSwitchBack } from '../character/useSwitchBack'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { DATING_STATUS_KEY, cardHeading, interestText } from './datingText'
import { Photo } from './Photo'
import { AboutYou, IntoWho, Setup, WhatYouWant } from './Setup'

const DATING_KEY = ['dating']

/** The dating app: swipe through townsfolk, and a match can become a companion. Older eras get a personal column. */
export function Dating({ go }: { go: (view: View) => void }) {
  const dating = useQuery({ queryKey: DATING_KEY, queryFn: () => api<DatingData>('/dating') })
  const client = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [matched, setMatched] = useState<DatingCard | null>(null)
  const [error, setError] = useState('')
  if (dating.isPending) return <Loading label="Opening the app" />
  if (dating.isError) return <ErrorNotice error={dating.error} />
  const data = dating.data
  const run = async (request: () => Promise<DatingData>) => {
    setError('')
    try {
      const next = await request()
      client.setQueryData(DATING_KEY, next)
      return next
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'That did not work. Try again.')
      return null
    }
  }
  const save = async (profile: DatingProfile) => {
    const next = await run(() => api<DatingData>('/dating/profile', profile, 'PUT'))
    await client.invalidateQueries({ queryKey: DATING_STATUS_KEY })
    return next
  }
  const swipe = async (key: string, like: boolean) => {
    const next = await run(() => api<DatingData>('/dating/swipes', { key, like }))
    if (next) setMatched(next.matched ?? null)
  }
  return (
    <section className="page dating" aria-labelledby="dating-heading">
      <header className="page-header"><div>
        <h1 id="dating-heading">{data.words.title}</h1>
        <p className="subtle">Meet people around town. Someone you match with can become a companion. Your companions never see who you swipe on.</p>
      </div></header>
      {error && <Notice tone="error">{error}</Notice>}
      {!data.profile ? <Setup words={data.words} surface={data.surface} onSave={async (profile) => { await save(profile) }} />
        : editing ? <ProfileForm profile={data.profile} onCancel={() => setEditing(false)} onSave={async (profile) => { if (await save(profile)) setEditing(false) }}
          onDelete={() => void run(() => api<DatingData>('/dating/profile', undefined, 'DELETE')).then(() => { setEditing(false); void client.invalidateQueries({ queryKey: DATING_STATUS_KEY }) })} />
        : <>
          <LookingIn data={data} onEdit={() => setEditing(true)} onMove={(cityId) => void run(() => api<DatingData>('/dating/city', { city_id: cityId }, 'PUT'))} />
          {data.date && <Notice action={<button type="button" className="text-button" onClick={() => void api('/dating/dates/current', undefined, 'DELETE').then(() => client.invalidateQueries())}>End the date</button>}>
            You are on a date with {data.date.name} in your story.</Notice>}
          {matched && <Notice action={<button type="button" className="text-button" onClick={() => go(`match/${encodeURIComponent(matched.key)}`)}>Start talking to {matched.name}…</button>}>
            {data.words.matched}: {matched.name} likes you too.</Notice>}
          <Deck data={data} onSwipe={(key, like) => void swipe(key, like)} onPassedAgain={() => void run(() => api<DatingData>('/dating/swipes/passed', undefined, 'DELETE'))} />
          <Matches data={data} go={go} onUnmatch={(key) => void run(() => api<DatingData>(`/dating/matches/${encodeURIComponent(key)}`, undefined, 'DELETE'))}
            onDate={async (key, placeId) => { await run(async () => { await api('/dating/dates', { key, place_id: placeId }); return api<DatingData>('/dating') }); go('story') }} />
        </>}
    </section>
  )
}

interface ProfileFormProps { profile: DatingProfile; onSave: (profile: DatingProfile) => Promise<void>; onCancel: () => void; onDelete: () => void }

/** Changing the profile later: every setup screen on one page, and a way to delete it. */
function ProfileForm({ profile, onSave, onCancel, onDelete }: ProfileFormProps) {
  const [draft, setDraft] = useState<DatingProfile>(profile)
  const [busy, setBusy] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const set = (change: Partial<DatingProfile>) => setDraft((old) => ({ ...old, ...change }))
  const ready = draft.age >= 18 && draft.age_min >= 18 && draft.age_min <= draft.age_max && draft.interested_in.length > 0
  return (
    <form className="form-stack dating-setup" onSubmit={(event) => { event.preventDefault(); setBusy(true); void onSave(draft).finally(() => setBusy(false)) }}>
      <h2>Your profile</h2>
      <AboutYou draft={draft} set={set} />
      <IntoWho draft={draft} set={set} />
      <WhatYouWant draft={draft} set={set} />
      <label>About you <textarea rows={3} maxLength={1000} value={draft.bio} onChange={(event) => set({ bio: event.target.value })} /></label>
      <div className="form-actions">
        <button type="submit" className="button primary" disabled={busy || !ready}>Save</button>
        <button type="button" className="text-button" onClick={onCancel}>Cancel</button>
        <button type="button" className="text-button" onClick={() => setDeleting(true)}>Delete your profile…</button>
      </div>
      {deleting && <ConfirmDialog title="Delete your profile?" onClose={() => setDeleting(false)} actions={<>
        <button type="button" className="button" onClick={() => setDeleting(false)}>Cancel</button>
        <button type="button" className="button primary" onClick={onDelete}>Delete</button>
      </>}><p>Your profile, likes and matches go for good. Anyone who already became a companion stays one.</p></ConfirmDialog>}
    </form>
  )
}

function LookingIn({ data, onEdit, onMove }: { data: DatingData; onEdit: () => void; onMove: (cityId: string) => void }) {
  const cities = useQuery({ queryKey: ['world-cities'], queryFn: () => api<CitySummary[]>('/world/cities') })
  const profile = data.profile!
  return (
    <div className="dating-bar">
      <label><MapPin aria-hidden="true" /> Looking in
        <select value={data.city.id} onChange={(event) => onMove(event.target.value)}>
          {(cities.data ?? [data.city]).map((city) => <option key={city.id} value={city.id}>{city.name}</option>)}
        </select>
      </label>
      <p className="subtle">{interestText(profile)} <button type="button" className="text-button inline" onClick={onEdit}>Edit your profile</button></p>
    </div>
  )
}

function Deck({ data, onSwipe, onPassedAgain }: { data: DatingData; onSwipe: (key: string, like: boolean) => void; onPassedAgain: () => void }) {
  const card = data.deck[0]
  if (!card) {
    return <div className="dating-empty"><p className="subtle">{data.words.empty}</p>
      <button type="button" className="text-button" onClick={onPassedAgain}>See people you passed on again</button></div>
  }
  return (
    <article className={`dating-card dating-${data.surface}`} aria-label={data.surface === 'column' ? 'A notice in the personal column' : `${card.name}, ${card.age}`}>
      {data.surface === 'column'
        ? <p className="dating-notice">{card.notice}</p>
        : <>
          {data.photos && <Photo key={card.key} personKey={card.key} name={card.name} />}
          <h2>{cardHeading(card)}</h2>
          {card.job && <p>{card.job} · {card.neighborhood}</p>}
          <p className="subtle">{card.looks}</p>
          <p>{card.bio}</p>
          <p className="subtle">Looking for {card.looking_text}.</p>
        </>}
      <div className="form-actions dating-actions">
        <button type="button" className="button" onClick={() => onSwipe(card.key, false)}><X aria-hidden="true" />{data.words.pass}</button>
        <button type="button" className="button primary" onClick={() => onSwipe(card.key, true)}><Heart aria-hidden="true" />{data.words.like}</button>
      </div>
      <p className="subtle">{data.remaining - 1 > 0 ? `${data.remaining - 1} more after this one.` : 'The last one for now.'}</p>
    </article>
  )
}

interface MatchesProps { data: DatingData; go: (view: View) => void; onUnmatch: (key: string) => void; onDate: (key: string, placeId: string) => Promise<void> }

function Matches({ data, go, onUnmatch, onDate }: MatchesProps) {
  const { switchTo, busy, error } = useSwitchBack(go)
  if (!data.matches.length) return null
  return (
    <section className="dating-matches" aria-labelledby="matches-heading">
      <h2 id="matches-heading">Your matches</h2>
      {error && <Notice tone="error">{error}</Notice>}
      <ul>
        {data.matches.map((match) => <li key={match.key}>
          <p><strong>{cardHeading(match)}</strong>{match.job ? ` · ${match.job}` : ''} · {match.city.name}</p>
          <div className="form-actions">
            {match.companion_id
              ? <button type="button" className="button primary" disabled={busy !== null} onClick={() => void switchTo(match.companion_id!)}>Talk to {match.name}</button>
              : <button type="button" className="button primary" onClick={() => go(`match/${encodeURIComponent(match.key)}`)}>Start talking to {match.name}…</button>}
            {data.story && <MeetInStory match={match} onDate={onDate} />}
            {!match.companion_id && <button type="button" className="text-button" onClick={() => onUnmatch(match.key)}>Unmatch</button>}
          </div>
        </li>)}
      </ul>
    </section>
  )
}

function MeetInStory({ match, onDate }: { match: DatingMatch; onDate: (key: string, placeId: string) => Promise<void> }) {
  const [open, setOpen] = useState(false)
  const [place, setPlace] = useState(match.places[0]?.id ?? '')
  if (!open) return <button type="button" className="button" onClick={() => setOpen(true)}>Meet in your story…</button>
  return (
    <span className="dating-date">
      <label>Where
        <select value={place} onChange={(event) => setPlace(event.target.value)}>
          {match.places.map((item) => <option key={item.id} value={item.id}>{item.name} ({item.kind}, {item.neighborhood}){item.theirs ? ' · their usual spot' : ''}</option>)}
        </select>
      </label>
      <button type="button" className="button primary" disabled={!place} onClick={() => void onDate(match.key, place)}>Go on the date</button>
      <button type="button" className="text-button" onClick={() => setOpen(false)}>Not now</button>
    </span>
  )
}
