import { Fragment, useRef, useState, type CSSProperties, type KeyboardEvent, type ReactNode, type RefObject } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Home, Map as MapIcon, MapPin, Pencil, RotateCcw, Send, Undo2 } from 'lucide-react'
import { api, newId } from '../../api'
import type { View } from '../../companion'
import type { CitySummary, Story as StoryData, StoryChapter, StoryMessage, StoryScene } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { InfoTip } from '../../components/InfoTip'
import { TextArea } from '../../components/Fields'
import { AiFooter, CrisisNote } from '../../components/Safety'
import { againLabel, aroundText, chapterWhen, cutShort, goHome, goneFrom, homeChoice, latestLine, numbered, openingAction, openingPlace, openingText, placeGroups, planText, sceneTime, spotsText, toldAgain, whereText, writingText } from './storyText'
import { StoryPeople } from './StoryPeople'
import { useEraWords } from '../world/useEraWords'
import { say } from '../world/eraWords'
import { ChapterHeading, LineTime, StoryFooter } from './StoryChapters'
import { useStoryScroll } from './useStoryScroll'
import { CityOptions } from '../world/CityOptions'
import { AuthorsNote } from '../conversation/AuthorsNote'
import { fitAfterSend, setFolded, useMessageBox } from '../conversation/messageBox'
import { MessageBox } from '../conversation/MessageBoxControls'
import { useGroupLookStyles } from '../conversation/useTheirLook'
import { useMessageSheet, type Action } from '../conversation/useMessageSheet'

const STORY_KEY = ['story']
/** While a sent line waits, the story is read again this often: the narrator's reply shows before a companion's. */
const WAITING_MS = 1500
/** A line the user sent that is still being answered. */
interface Pending { text: string; clientId: string }
/** How far down the story is read before the phone's header folds to the place and the people count. */
const FOLD_AFTER = 8
const OUT_OF_STORY = 'To step out of the story, start a message with OOC: or wrap it in ((double parentheses)).'

function failed(failure: unknown): string {
  return failure instanceof Error ? failure.message : 'That did not work. Try again.'
}

/** Whether the header is folded: once the story is scrolled down, until it is back at the top (the phone's styles
 * alone act on it). Folding hands the header's room to the story, so it waits until there is more than that left
 * to scroll (`room`): with less, the story would fit, spring back to its top and unfold again, and its newest
 * lines could never be reached. */
function useFold(section: RefObject<HTMLElement | null>) {
  const [folded, setFolded] = useState(false)
  const onScrolled = (top: number, room: number) => setFolded((now) => {
    if (now) return top > 0
    return top > FOLD_AFTER && room > (section.current?.querySelector<HTMLElement>('.story-header')?.offsetHeight ?? 0)
  })
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
  const section = useRef<HTMLElement>(null)
  const [folded, onScrolled] = useFold(section)
  const [editing, setEditing] = useState<StoryMessage | null>(null)
  const lookFor = useNameLooks(section, story.data)
  if (story.isPending) return <Loading label="Opening your story" />
  if (story.isError) return <ErrorNotice error={story.error} />
  const update = (data: StoryData) => client.setQueryData(STORY_KEY, data)
  const run = async (sent: Pending | null, request: () => Promise<unknown>) => {
    setPending(sent)
    setBusy(true)
    setError('')
    try { await request() } catch (failure) { setError(failed(failure)) }
    finally { await client.invalidateQueries({ queryKey: STORY_KEY }); setPending(null); setBusy(false) }
  }
  const send = (text: string) => { const clientId = newId(); return run({ text, clientId }, () => api('/story/messages', { text, client_id: clientId })) }
  const find = (key: string) => api<StoryData>('/story/find', { key }).then(update)
  /** The latest line answered again: its reply told again in its place, or with `text` the line said differently
   * (companion/story_again.py). The replies told before go at once; the new ones arrive one speaker at a time. */
  const again = (line: StoryMessage, text?: string) => {
    update({ ...story.data, messages: toldAgain(story.data.messages, line, text) })
    return run({ text: '', clientId: line.client_id ?? '' }, () => text ? api(`/story/messages/${line.id}`, { text }, 'PUT') : api('/story/retry', {}))
  }
  /** Undo on Another reply: the reply that was there before is back, with what it had done. Nothing is written. */
  const undo = () => run(null, () => api('/story/retry/undo', {}))
  /** The narrator's reply or a companion's line in the user's wording, in place: nothing is written again, and the
   * page stays where it is, since the line may be far up the story. */
  const reword = async (line: StoryMessage, text: string) => {
    update({ ...story.data, messages: story.data.messages.map((message) => (message.id === line.id ? { ...message, text } : message)) })
    setError('')
    try { await api(`/story/messages/${line.id}`, { text }, 'PUT') } catch (failure) { setError(failed(failure)) }
    finally { await client.invalidateQueries({ queryKey: STORY_KEY }) }
  }
  /** Start a new chapter of the same story, or take that back: nothing is cleared (companion/story_chapters.py). */
  const chapter = (method: 'POST' | 'DELETE') => run(null, () => api<StoryData>('/story/chapter', undefined, method).then(update))
  const main = story.data.companions.find((companion) => companion.main)
  /** The first-open button: go to the companion when they are somewhere else the story can go, then say the first line.
   * A plan under way takes no line from the user: the button goes to it, or starts its scene. */
  const start = () => {
    const action = openingAction(main, story.data.scene.plan)
    const clientId = newId()
    if (action.begin) return run({ text: '', clientId }, () => api('/story/begin', { client_id: clientId }))
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
          onFind={(key) => void run(null, () => find(key))} onSay={(line) => void send(line)} busy={busy} />
      </header>
      {!story.data.ready && <div className="story-notice"><Notice action={<button type="button" className="text-button" onClick={() => go('settings/models')}>Open Models</button>}>
        Add a text model in Settings &gt; Models to tell the story.</Notice></div>}
      <Opening at="top" story={story.data} busy={busy} onStart={() => void start()} />
      <StoryLog messages={story.data.messages} pending={pending} companions={story.data.scene.companions} lookFor={lookFor}
        chapters={story.data.chapters} next={pending ? null : story.data.next_chapter} onUndo={() => void chapter('DELETE')}
        onScrolled={onScrolled} busy={busy} onAgain={(line) => void again(line)} onUndoReply={() => void undo()} onEdit={(line) => { if (!busy) setEditing(line) }} onModels={() => go('settings/models')} />
      <Opening at="bottom" story={story.data} busy={busy} onStart={() => void start()} />
      {error && <div className="story-notice"><Notice tone="error">{error}</Notice></div>}
      <StoryComposer busy={busy} onSend={(text) => void send(text)} />
      {editing && <EditLine line={editing} onClose={() => setEditing(null)} onSave={(text) => { setEditing(null); void (editing.role === 'user' ? again(editing, text) : reword(editing, text)) }} />}
      <StoryFooter empty={!story.data.messages.length} waiting={!!story.data.next_chapter} busy={busy} onChapter={() => void chapter('POST')}
        onClear={() => run(null, () => api<StoryData>('/story', undefined, 'DELETE').then(update))} />
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
      <p>{aroundText(scene.around, scene.place.home)}</p>
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

/** Going somewhere else: home in one press, first and apart (Iris, 2026-11-26), then a city and a place in it. The
 * story also follows what the user writes (companion/life/scene_now.py). */
function GoElsewhere({ scene, onDone, onMove }: GoProps) {
  const cities = useQuery({ queryKey: ['world-cities'], queryFn: () => api<CitySummary[]>('/world/cities') })
  const [place, setPlace] = useState(scene.place.id)
  const home = goHome(scene)
  const here = homeChoice(scene)
  return (
    <div className="story-go form-actions">
      {home && <div className="story-go-home"><button type="button" className="button" onClick={() => void onMove(home).then(onDone)}><Home aria-hidden="true" />Go home</button></div>}
      <label>City
        <select value={scene.city.id} onChange={(event) => void onMove({ city_id: event.target.value })}>
          <CityOptions cities={cities.data ?? [scene.city]} />
        </select>
      </label>
      <label>Place
        <select value={place} onChange={(event) => setPlace(event.target.value)}>
          {here && <option value={here.id}>{here.name}</option>}
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
  lookFor: (companionId: string | null) => CSSProperties | undefined; onScrolled: (top: number, room: number) => void
  /** The chapters the lines are in, and the one waiting for its first line (companion/story_chapters.py). */
  chapters: StoryChapter[]; next: StoryChapter | null; onUndo: () => void  // `next` is null while a line is being answered.
  /** Under the newest reply (companion/story_again.py): told again, the one before brought back, a line edited. */
  busy: boolean; onAgain: (line: StoryMessage) => void; onUndoReply: () => void; onEdit: (line: StoryMessage) => void
  /** Opens Settings > Models, where "Longest reply" is, from the note on a reply that was cut short. */
  onModels: () => void
}

function StoryLog({ messages, pending, companions, lookFor, chapters, next, onUndo, onScrolled, busy, onAgain, onUndoReply, onEdit, onModels }: LogProps) {
  const end = useRef<HTMLDivElement>(null)
  const line = busy ? null : latestLine(messages)
  // Again once the replies are all in: Another reply and Edit your line show under them then.
  useStoryScroll(end, messages.length, pending ?? `${next?.number ?? ''}:${line ? 'answered' : ''}`)
  return (
    <div className="story-log" aria-live="polite" onScroll={(event) => onScrolled(event.currentTarget.scrollTop, event.currentTarget.scrollHeight - event.currentTarget.clientHeight)}>
      <StoryLines messages={messages} chapters={chapters} headed={numbered(chapters, next)} lookFor={lookFor} onEdit={onEdit} />
      {line && <LatestActions messages={messages} line={line} onAgain={onAgain} onUndo={onUndoReply} onEdit={onEdit} onModels={onModels} />}
      {next && <ChapterHeading chapter={next} onUndo={onUndo} />}
      {pending && <Writing messages={messages} pending={pending} companions={companions} />}
      <div ref={end} />
    </div>
  )
}

/** While a line is answered. The sent line shows from here until the story read again has it; its replies then
 * arrive one speaker at a time. */
function Writing({ messages, pending, companions }: { messages: StoryMessage[]; pending: Pending; companions: { id: string; name: string }[] }) {
  const saved = messages.some((message) => message.client_id === pending.clientId)
  return <>{!saved && pending.text && <p className="story-user">{pending.text}</p>}<p className="subtle">{writingText(messages, pending.clientId, companions)}</p></>
}

/** Under the story's newest reply, as under a chat's: the reply told again in its place (Try again when one failed or
 * never came), and the line it answers said differently. A story has one course, so only the latest line has them,
 * and only until the story goes on. A line the app said to start a plan's scene is not the user's to change. After
 * Another reply, Undo brings back the reply that was there, until the next line is sent. A reply the service cut
 * short at the reply limit says so here, before the buttons, and only while it is the newest (Iris, 1.5.2): nothing
 * failed, so it is a quiet line, and the reply above already ends on a full sentence. */
function LatestActions({ messages, line, onAgain, onUndo, onEdit, onModels }: Pick<LogProps, 'messages' | 'onAgain' | 'onEdit' | 'onModels'> & { line: StoryMessage; onUndo: () => void }) {
  const cut = cutShort(messages, line)
  // Pressing one must not take the cursor out of the message box: on a phone the tab bar comes back when it does,
  // everything moves up under the finger, and the tap lands on nothing.
  return (
    <div className="turn-actions story-actions" onMouseDown={(event) => event.preventDefault()}>
      {cut && <p className="subtle story-cut">{cut} <a className="text-button inline" href="#settings/models" onClick={(event) => { event.preventDefault(); onModels() }}>longest reply limit</a></p>}
      <button type="button" className="text-button" onClick={() => onAgain(line)}><RotateCcw aria-hidden="true" />{againLabel(messages, line)}</button>
      {line.undo && <button type="button" className="text-button" onClick={onUndo}><Undo2 aria-hidden="true" />Undo<span className="visually-hidden">: bring back the reply before</span></button>}
      {!line.hidden && <button type="button" className="text-button" onClick={() => onEdit(line)}><Pencil aria-hidden="true" />Edit your line</button>}
    </div>
  )
}

/** What the edit dialog says for a line: the user's own latest line is answered anew, a reply is reworded in place. */
function editWords(line: StoryMessage): { title: string; label: string; hint: string } {
  if (line.role === 'user') return { title: 'Edit your line', label: 'What you do or say', hint: 'The reply is written again from your new words.' }
  const whose = line.role === 'companion' ? `${line.name}'s line` : "the narrator's reply"
  return { title: `Edit ${whose}`, label: `${whose.charAt(0).toUpperCase()}${whose.slice(1)}`, hint: 'The story goes on from the new wording.' }
}

/** Edit on a line of the story (companion/story_again.py): the user's latest line, said differently, or the
 * narrator's reply or a companion's line in the user's wording. */
function EditLine({ line, onClose, onSave }: { line: StoryMessage; onClose: () => void; onSave: (text: string) => void }) {
  const [text, setText] = useState(line.text)
  const changed = !!text.trim() && text.trim() !== line.text
  const words = editWords(line)
  return (
    <ConfirmDialog title={words.title} onClose={onClose} actions={<>
      <button type="button" className="button" onClick={onClose}>Cancel</button>
      <button type="button" className="button primary" disabled={!changed} onClick={() => onSave(text.trim())}>Save</button>
    </>}>
      <TextArea label={words.label} labelHidden value={text} onChange={setText} rows={line.role === 'user' ? 4 : 10} maxLength={40000} hint={words.hint} />
    </ConfirmDialog>
  )
}

/** The lines in their chapters: a chapter's heading stands above its first line (companion/story_chapters.py),
 * once the story has more than one (`headed`). */
function StoryLines({ messages, chapters, headed, lookFor, onEdit }: Pick<LogProps, 'messages' | 'chapters' | 'lookFor' | 'onEdit'> & { headed: boolean }) {
  return <>{messages.map((message, index) => {
    const chapter = chapters.find((item) => item.number === message.chapter)
    return <Fragment key={message.id}>
      {headed && chapter && messages[index - 1]?.chapter !== message.chapter && <ChapterHeading chapter={chapter} />}
      <StoryLine message={message} began={chapter?.local_time} look={message.speaker ? lookFor(message.speaker) : undefined} onEdit={onEdit} />
    </Fragment>
  })}</>
}

/** One of the app's own lines: an arrival, or who came and went. When a companion leaves, the line offers their
 * chat: the two of them are apart again. */
function MoveLine({ message, time }: { message: StoryMessage; time: ReactNode }) {
  const words = useEraWords()
  const gone = goneFrom(message)
  return <p className="story-move">{message.text} {time}{gone && <> · <a className="text-button inline" href={`#chat/${gone}`}>{say(words, 'message_to', message.name ?? '')}</a></>}</p>
}

function StoryLine({ message, began, look, onEdit }: { message: StoryMessage; began?: string; look?: CSSProperties; onEdit: (line: StoryMessage) => void }) {
  const time = <LineTime at={message.local_time} began={began} />
  if (message.role === 'scene' || message.role === 'cast') return <MoveLine message={message} time={time} />
  if (message.hidden) return null
  if (message.role === 'user') return <><div className="story-mine"><p className="story-user">{message.text}</p>{time}</div>{message.crisis_help && <CrisisNote />}</>
  if (message.status === 'failed') return <Notice tone="error">{message.role === 'companion' ? `${message.name} could not answer` : 'The narrator could not go on'}: {message.error}</Notice>
  return <StoryReply message={message} look={look} onEdit={onEdit} />
}

/** The narrator's reply, or a companion's own line under their name (their character wrote it, not the narrator).
 * Either can be reworded: Edit shows on it with a mouse or the keyboard, and on a touch screen it is pressed and
 * held for its sheet, as a chat's messages are (useMessageSheet.tsx). */
function StoryReply({ message, look, onEdit }: { message: StoryMessage; look?: CSSProperties; onEdit: (line: StoryMessage) => void }) {
  // A reply shows no time of its own: it comes moments after the line above it. Pointing at it says when.
  const when = chapterWhen(message.local_time)
  const actions: Action<StoryMessage>[] = [['Edit', <Pencil key="icon" aria-hidden="true" />, onEdit]]
  const sheet = useMessageSheet(message, actions)
  const said = message.role === 'companion'
  const parts = message.text.split(/\n{2,}/).map((part, index) => <p key={index}>{part}</p>)
  return (
    <div className={`story-reply ${said ? `story-said${look ? ' their-name' : ''}` : 'story-narration'}${sheet.pressing ? ' pressing' : ''}`} style={look} title={when} {...sheet.press}>
      {said && <p className="story-speaker">{message.name}</p>}
      {parts}
      <span className="story-tools"><button type="button" className="text-button" onClick={() => onEdit(message)}><Pencil aria-hidden="true" />Edit<span className="visually-hidden"> {said ? `${message.name}'s line` : "the narrator's reply"}</span></button></span>
      {sheet.sheet}
    </div>
  )
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
