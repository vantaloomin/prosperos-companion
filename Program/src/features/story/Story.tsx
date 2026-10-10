import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { MapPin, RotateCcw, Send } from 'lucide-react'
import { api, newId } from '../../api'
import type { View } from '../../companion'
import type { CitySummary, Story as StoryData, StoryMessage, StoryScene } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { InfoTip } from '../../components/InfoTip'
import { AiFooter, CrisisNote } from '../../components/Safety'
import { aroundText, placeGroups, sceneTime, spotsText, whereText } from './storyText'
import { StoryPeople } from './StoryPeople'

const STORY_KEY = ['story']
const OUT_OF_STORY = 'To step out of the story, start a message with OOC: or wrap it in ((double parentheses)).'

/** Story mode: the user's own story around the cities, told by a narrator. The companion never sees it. */
export function Story({ go }: { go: (view: View) => void }) {
  const story = useQuery({ queryKey: STORY_KEY, queryFn: () => api<StoryData>('/story') })
  const client = useQueryClient()
  const [pending, setPending] = useState<string | null>(null)
  const [error, setError] = useState('')
  if (story.isPending) return <Loading label="Opening your story" />
  if (story.isError) return <ErrorNotice error={story.error} />
  const update = (data: StoryData) => client.setQueryData(STORY_KEY, data)
  const run = async (text: string | null, request: () => Promise<unknown>) => {
    setPending(text)
    setError('')
    try { await request() } catch (failure) { setError(failure instanceof Error ? failure.message : 'That did not work. Try again.') }
    finally { setPending(null); await client.invalidateQueries({ queryKey: STORY_KEY }) }
  }
  const send = (text: string) => run(text, () => api('/story/messages', { text, client_id: newId() }))
  return (
    <section className="story" aria-labelledby="story-heading">
      <header className="story-header">
        <h1 id="story-heading">Story</h1>
        <p className="subtle">Your own story around town, told by a narrator. Your companion never sees it.</p>
        <SceneBar scene={story.data.scene} onMove={(body) => run(null, () => api<StoryData>('/story/scene', body, 'PUT').then(update))} />
        <StoryPeople people={story.data.people} canSwitch={story.data.can_switch} go={go}
          onFind={(key) => void run(null, () => api<StoryData>('/story/find', { key }).then(update))} />
      </header>
      {!story.data.ready && <div className="story-notice"><Notice action={<button type="button" className="text-button" onClick={() => go('settings/models')}>Open Models</button>}>
        Add a text model in Settings &gt; Models to tell the story.</Notice></div>}
      <StoryLog messages={story.data.messages} pending={pending} onRetry={() => void run(null, () => api('/story/retry', {}))} />
      {error && <div className="story-notice"><Notice tone="error">{error}</Notice></div>}
      <StoryComposer busy={pending !== null} onSend={(text) => void send(text)} />
      <NewStory empty={!story.data.messages.length} onClear={() => run(null, () => api<StoryData>('/story', undefined, 'DELETE').then(update))} />
    </section>
  )
}

function SceneBar({ scene, onMove }: { scene: StoryScene; onMove: (body: { city_id: string; place_id?: string }) => Promise<void> }) {
  const [moving, setMoving] = useState(false)
  return (
    <div className="story-scene">
      <p><MapPin aria-hidden="true" /> <strong>{whereText(scene)}</strong></p>
      <p className="subtle">{sceneTime(scene.local_time)}{scene.weather ? ` · ${scene.weather}` : ''}</p>
      {!!scene.place.spots?.length && <p className="subtle">{spotsText(scene.place.spots)}</p>}
      <p>{aroundText(scene.around)}</p>
      {moving ? <GoElsewhere scene={scene} onDone={() => setMoving(false)} onMove={onMove} />
        : <button type="button" className="button" onClick={() => setMoving(true)}>Go somewhere else…</button>}
    </div>
  )
}

interface GoProps { scene: StoryScene; onDone: () => void; onMove: (body: { city_id: string; place_id?: string }) => Promise<void> }

function GoElsewhere({ scene, onDone, onMove }: GoProps) {
  const cities = useQuery({ queryKey: ['world-cities'], queryFn: () => api<CitySummary[]>('/world/cities') })
  const [place, setPlace] = useState(scene.place.id)
  return (
    <div className="story-go form-actions">
      <label>City
        <select value={scene.city.id} onChange={(event) => void onMove({ city_id: event.target.value })}>
          {(cities.data ?? [scene.city]).map((city) => <option key={city.id} value={city.id}>{city.name}</option>)}
        </select>
      </label>
      <label>Place
        <select value={place} onChange={(event) => setPlace(event.target.value)}>
          {placeGroups(scene.places).map(([hood, places]) => (
            <optgroup key={hood} label={hood}>
              {places.map((item) => <option key={item.id} value={item.id}>{item.name} ({item.kind})</option>)}
            </optgroup>))}
        </select>
      </label>
      <button type="button" className="button primary" onClick={() => void onMove({ city_id: scene.city.id, place_id: place }).then(onDone)}>Go</button>
      <button type="button" className="text-button" onClick={onDone}>Stay here</button>
    </div>
  )
}

function StoryLog({ messages, pending, onRetry }: { messages: StoryMessage[]; pending: string | null; onRetry: () => void }) {
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => { end.current?.scrollIntoView?.({ block: 'end' }) }, [messages.length, pending])
  const last = messages[messages.length - 1]
  return (
    <div className="story-log" aria-live="polite">
      {!messages.length && !pending && <p className="subtle story-empty">Say what you do first: look around, order something, talk to someone.</p>}
      {messages.map((message) => <StoryLine key={message.id} message={message} />)}
      {pending && <><p className="story-user">{pending}</p><p className="subtle">The narrator is writing…</p></>}
      {last?.status === 'failed' && !pending && <button type="button" className="text-button" onClick={onRetry}><RotateCcw aria-hidden="true" />Try again</button>}
      <div ref={end} />
    </div>
  )
}

function StoryLine({ message }: { message: StoryMessage }) {
  if (message.role === 'scene') return <p className="story-move">{message.text}</p>
  if (message.role === 'user') return <><p className="story-user">{message.text}</p>{message.crisis_help && <CrisisNote />}</>
  if (message.status === 'failed') return <Notice tone="error">The narrator could not go on: {message.error}</Notice>
  return <div className="story-narration">{message.text.split(/\n{2,}/).map((part, index) => <p key={index}>{part}</p>)}</div>
}

function StoryComposer({ busy, onSend }: { busy: boolean; onSend: (text: string) => void }) {
  const [text, setText] = useState('')
  const submit = () => { if (text.trim() && !busy) { onSend(text.trim()); setText('') } }
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); submit() }
  }
  return (<>
    <form className="composer story-composer" onSubmit={(event) => { event.preventDefault(); submit() }}>
      <label className="visually-hidden" htmlFor="story-text">What you do or say</label>
      <textarea id="story-text" rows={2} value={text} maxLength={40000} placeholder="What do you do or say?"
        onChange={(event) => setText(event.target.value)} onKeyDown={onKeyDown} />
      <InfoTip id="story-tip" label="the story" above text={`Enter sends, Shift+Enter adds a new line. ${OUT_OF_STORY}`} />
      <button type="submit" className="button primary" disabled={busy || !text.trim()}><Send aria-hidden="true" />Send</button>
    </form>
    <AiFooter />
  </>)
}

function NewStory({ empty, onClear }: { empty: boolean; onClear: () => Promise<void> }) {
  const [asking, setAsking] = useState(false)
  if (empty) return null
  return (
    <div className="story-footer">
      <button type="button" className="text-button" onClick={() => setAsking(true)}>Start a new story…</button>
      {asking && <ConfirmDialog title="Start a new story?" onClose={() => setAsking(false)} actions={<>
        <button type="button" className="button" onClick={() => setAsking(false)}>Cancel</button>
        <button type="button" className="button primary" onClick={() => void onClear().then(() => setAsking(false))}>Start a new story</button>
      </>}>
        <p>The story so far and the people you&apos;ve met in it are cleared for good. You stay where you are.</p>
      </ConfirmDialog>}
    </div>
  )
}
