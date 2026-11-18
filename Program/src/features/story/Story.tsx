import { useEffect, useRef, useState, type CSSProperties, type KeyboardEvent, type RefObject } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Map as MapIcon, MapPin, RotateCcw, Send } from 'lucide-react'
import { api, newId } from '../../api'
import type { View } from '../../companion'
import type { CitySummary, Story as StoryData, StoryMessage, StoryScene } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { InfoTip } from '../../components/InfoTip'
import { AiFooter, CrisisNote } from '../../components/Safety'
import { aroundText, openingAction, openingPlace, openingText, placeGroups, planText, sceneTime, spotsText, whereText, writingText } from './storyText'
import { StoryPeople } from './StoryPeople'
import { CityOptions } from '../world/CityOptions'
import { ExportLinks } from '../chats/ExportLinks'
import { AuthorsNote } from '../conversation/AuthorsNote'
import { fitAfterSend, setFolded, useMessageBox } from '../conversation/messageBox'
import { MessageBox } from '../conversation/MessageBoxControls'
import { useGroupLookStyles } from '../conversation/useTheirLook'

const STORY_KEY = ['story']
/** While a sent line waits, the story is read again this often: the narrator's reply shows before a companion's. */
const WAITING_MS = 1500
/** A line the user sent that is still being answered. */
interface Pending { text: string; clientId: string }
/** How far down the story is read before the phone's header folds to the place and the people count. */
const FOLD_AFTER = 8
const OUT_OF_STORY = 'To step out of the story, start a message with OOC: or wrap it in ((double parentheses)).'

/** Whether the header is folded: once the story is scrolled down, until it is back at the top (the phone's styles
 * alone act on it). */
function useFold() {
  const [folded, setFolded] = useState(false)
  const onScrolled = (top: number) => setFolded((now) => top > FOLD_AFTER ? true : top <= 0 ? false : now)
  return [folded, onScrolled] as const
}

/** Each companion's name in their own colour, as in their chats (Their look). */
function useNameLooks(section: RefObject<HTMLElement | null>, story?: StoryData) {
  return useGroupLookStyles(section, (story?.companions ?? []).map((companion) => ({ companion_id: companion.id })))
}

/** Story: the user's own story around the cities, told by a narrator. A companion who is where the story is at
 * that hour is in the scene and answers in their own lines (companion/story_cast.py). */
export function Story({ go }: { go: (view: View) => void }) {
  const [pending, setPending] = useState<Pending | null>(null)
  const story = useQuery({ queryKey: STORY_KEY, queryFn: () => api<StoryData>('/story'), refetchInterval: pending ? WAITING_MS : false })
  const client = useQueryClient()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [folded, onScrolled] = useFold()
  const section = useRef<HTMLElement>(null)
  const lookFor = useNameLooks(section, story.data)
  if (story.isPending) return <Loading label="Opening your story" />
  if (story.isError) return <ErrorNotice error={story.error} />
  const update = (data: StoryData) => client.setQueryData(STORY_KEY, data)
  const run = async (sent: Pending | null, request: () => Promise<unknown>) => {
    setPending(sent)
    setBusy(true)
    setError('')
    try { await request() } catch (failure) { setError(failure instanceof Error ? failure.message : 'That did not work. Try again.') }
    finally { await client.invalidateQueries({ queryKey: STORY_KEY }); setPending(null); setBusy(false) }
  }
  const send = (text: string) => { const clientId = newId(); return run({ text, clientId }, () => api('/story/messages', { text, client_id: clientId })) }
  const find = (key: string) => api<StoryData>('/story/find', { key }).then(update)
  const main = story.data.companions.find((companion) => companion.main)
  /** The first-open button: go to the companion when they are somewhere else the story can go, then say the first line.
   * A plan under way takes no line from the user: the button goes to it, or starts its scene. */
  const start = () => {
    const action = openingAction(main, story.data.scene.plan)
    const clientId = newId()
    if (action.begin) return run({ text: '', clientId }, () => api('/story/plan/begin', { client_id: clientId }))
    if (!action.line) return run(null, () => find(action.find ?? ''))
    return run({ text: action.line, clientId }, async () => {
      if (action.find) await find(action.find)
      await api('/story/messages', { text: action.line, client_id: clientId })
    })
  }
  return (
    <section ref={section} className="story" aria-labelledby="story-heading">
      <header className={`story-header${folded ? ' story-header-folded' : ''}`}>
        <h1 id="story-heading">Story</h1>
        <SceneBar scene={story.data.scene} onMap={() => go(`map/${encodeURIComponent(story.data.scene.place.id)}`)} onMove={(body) => run(null, () => api<StoryData>('/story/scene', body, 'PUT').then(update))} />
        <StoryPeople people={story.data.people} companions={story.data.companions} city={story.data.scene.city.name} canSwitch={story.data.can_switch} go={go}
          onFind={(key) => void run(null, () => find(key))} />
      </header>
      {!story.data.ready && <div className="story-notice"><Notice action={<button type="button" className="text-button" onClick={() => go('settings/models')}>Open Models</button>}>
        Add a text model in Settings &gt; Models to tell the story.</Notice></div>}
      <Opening at="top" story={story.data} busy={busy} onStart={() => void start()} />
      <StoryLog messages={story.data.messages} pending={pending} companions={story.data.scene.companions} lookFor={lookFor}
        onScrolled={onScrolled} onRetry={() => void run(null, () => api('/story/retry', {}))} />
      <Opening at="bottom" story={story.data} busy={busy} onStart={() => void start()} />
      {error && <div className="story-notice"><Notice tone="error">{error}</Notice></div>}
      <StoryComposer busy={busy} onSend={(text) => void send(text)} />
      <NewStory empty={!story.data.messages.length} onClear={() => run(null, () => api<StoryData>('/story', undefined, 'DELETE').then(update))} />
    </section>
  )
}

/** A story with nothing in it yet: what it is in one line and one way in. The button says the first line for the
 * user (none when a plan is under way); the box below takes any other. Without a model the notice above says what is needed instead. A plan under way
 * here (companion/story_plans.py) opens the same way under the lines that say who came, until something is said. */
function Opening({ at, story, busy, onStart }: { at: 'top' | 'bottom'; story: StoryData; busy: boolean; onStart: () => void }) {
  if (busy || openingPlace(story) !== at) return null
  const companion = story.companions.find((item) => item.main)
  const text = openingText(story.scene, companion)
  return (
    <div className="story-opening">
      {text && <p>{text}</p>}
      {story.ready && <button type="button" className="button primary" onClick={onStart}>{openingAction(companion, story.scene.plan).label}</button>}
    </div>
  )
}

function SceneBar({ scene, onMap, onMove }: { scene: StoryScene; onMap: () => void; onMove: (body: { city_id: string; place_id?: string }) => Promise<void> }) {
  const [moving, setMoving] = useState(false)
  return (
    <div className="story-scene">
      <p><MapPin aria-hidden="true" /> <strong>{whereText(scene)}</strong></p>
      <p className="subtle">{sceneTime(scene.local_time)}{scene.weather ? ` · ${scene.weather}` : ''}</p>
      {!!scene.place.spots?.length && <p className="subtle">{spotsText(scene.place.spots)}</p>}
      <p>{aroundText(scene.around)}</p>
      {scene.plan && <p className="story-plan">{planText(scene.plan)}</p>}
      {scene.plan?.storyline && <p>Part of a storyline.</p>}
      {moving ? <GoElsewhere scene={scene} onDone={() => setMoving(false)} onMove={onMove} />
        : <div className="form-actions">
          <button type="button" className="button" onClick={() => setMoving(true)}>Go somewhere else…</button>
          <button type="button" className="button" onClick={onMap}><MapIcon aria-hidden="true" />Map</button>
        </div>}
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
          <CityOptions cities={cities.data ?? [scene.city]} />
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

interface LogProps {
  messages: StoryMessage[]; pending: Pending | null; companions: { id: string; name: string }[]
  lookFor: (companionId: string | null) => CSSProperties | undefined; onScrolled: (top: number) => void; onRetry: () => void
}

function StoryLog({ messages, pending, companions, lookFor, onScrolled, onRetry }: LogProps) {
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => { end.current?.scrollIntoView?.({ block: 'end' }) }, [messages.length, pending])
  const last = messages[messages.length - 1]
  // The sent line shows from here until the story read again has it; its replies then arrive one speaker at a time.
  const saved = pending !== null && messages.some((message) => message.client_id === pending.clientId)
  return (
    <div className="story-log" aria-live="polite" onScroll={(event) => onScrolled(event.currentTarget.scrollTop)}>
      {messages.map((message) => <StoryLine key={message.id} message={message} look={message.speaker ? lookFor(message.speaker) : undefined} />)}
      {pending && <>{!saved && pending.text && <p className="story-user">{pending.text}</p>}<p className="subtle">{writingText(messages, pending.clientId, companions)}</p></>}
      {last?.status === 'failed' && !pending && <button type="button" className="text-button" onClick={onRetry}><RotateCcw aria-hidden="true" />Try again</button>}
      <div ref={end} />
    </div>
  )
}

function StoryLine({ message, look }: { message: StoryMessage; look?: CSSProperties }) {
  if (message.role === 'scene' || message.role === 'cast') return <p className="story-move">{message.text}</p>
  if (message.hidden) return null
  if (message.role === 'user') return <><p className="story-user">{message.text}</p>{message.crisis_help && <CrisisNote />}</>
  const parts = message.text.split(/\n{2,}/).map((part, index) => <p key={index}>{part}</p>)
  if (message.role === 'companion') {
    // A companion's own line, under their name: their character wrote it, not the narrator.
    if (message.status === 'failed') return <Notice tone="error">{message.name} could not answer: {message.error}</Notice>
    return <div className={`story-said${look ? ' their-name' : ''}`} style={look}><p className="story-speaker">{message.name}</p>{parts}</div>
  }
  if (message.status === 'failed') return <Notice tone="error">The narrator could not go on: {message.error}</Notice>
  return <div className="story-narration">{parts}</div>
}

function StoryComposer({ busy, onSend }: { busy: boolean; onSend: (text: string) => void }) {
  const [text, setText] = useState('')
  const { text: box, folded } = useMessageBox(text)
  const submit = () => { if (text.trim() && !busy) { onSend(text.trim()); setText(''); fitAfterSend() } }
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); submit() }
  }
  return (<>
    <form className="composer story-composer" onSubmit={(event) => { event.preventDefault(); submit() }}>
      <AuthorsNote chat="story" story />
      <label className="visually-hidden" htmlFor="story-text">What you do or say</label>
      <MessageBox text={box} folded={folded}>
        <textarea ref={box} id="story-text" rows={2} value={text} maxLength={40000} placeholder="What do you do or say?" onFocus={() => setFolded(false)}
          onChange={(event) => setText(event.target.value)} onKeyDown={onKeyDown} />
      </MessageBox>
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
      <ExportLinks target={{ kind: 'story' }} />
      <button type="button" className="text-button" onClick={() => setAsking(true)}>Start a new story…</button>
      {asking && <ConfirmDialog title="Start a new story?" onClose={() => setAsking(false)} actions={<>
        <button type="button" className="button" onClick={() => setAsking(false)}>Cancel</button>
        <button type="button" className="button primary" onClick={() => void onClear().then(() => setAsking(false))}>Start a new story</button>
      </>}>
        <p>The story so far and the people you&apos;ve met in it are cleared for good. You stay where you are.</p>
        <p className="subtle">To keep a copy, export it first:</p>
        <p className="form-actions"><ExportLinks target={{ kind: 'story' }} /></p>
      </ConfirmDialog>}
    </div>
  )
}
