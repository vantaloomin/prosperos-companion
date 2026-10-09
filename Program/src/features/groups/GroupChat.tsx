import { Fragment, useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDown, ChevronLeft, HeartHandshake, Pencil, RotateCcw, UsersRound } from 'lucide-react'
import { api, ApiError } from '../../api'
import { useWorkspaceSettings, type View } from '../../companion'
import type { Backstory, CastMember, Group, GroupChat as GroupChatData, GroupMember, GroupMessage, GroupMood } from '../../types'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { Stamp } from '../../components/Stamp'
import { CrisisNote } from '../../components/Safety'
import { useReturnFocus } from '../../components/returnFocus'
import { Composer } from '../conversation/Composer'
import { ChatsButton, ChatStyleSwitch } from '../conversation/ConversationHeader'
import { ChatSidebar } from '../chats/ChatSidebar'
import { ChatsPanel } from '../chats/ChatsPanel'
import { useMarkRead } from '../chats/useChats'
import { useChatStyle } from '../conversation/useChatStyle'
import { useDraft } from '../conversation/useDraft'
import { useOoc } from '../conversation/useOoc'
import { useScrollAway } from '../conversation/useScrollAway'
import { Backstories } from './Backstories'
import { NewGroup } from './Groups'
import { chatKey, GROUPS_KEY, useCast } from './groupState'
import { canRetry, failureText, groupActivity, membersLine, shownMessages, toldOnly } from './groupText'
import { guardNote } from './secretText'

// While replies are being written, the chat asks for what is new this often.
const POLL_MS = 700

type Notice = { tone: 'info' | 'error'; text: string; settings?: boolean } | null
type Change = (request: () => Promise<unknown>) => Promise<void>

/** The chat's data, kept fresh while replies are written, and the actions that change it. */
function useGroupChat(id: string) {
  const client = useQueryClient()
  const [sending, setSending] = useState(false)
  const [notice, setNotice] = useState<Notice>(null)
  const chat = useQuery({ queryKey: chatKey(id), queryFn: () => api<GroupChatData>(`/groups/${id}`),
    refetchInterval: (query) => query.state.data?.busy || sending ? POLL_MS : false })
  const refresh = () => Promise.all([client.invalidateQueries({ queryKey: chatKey(id) }), client.invalidateQueries({ queryKey: GROUPS_KEY })])
  const fail = (error: unknown) => setNotice({ tone: 'error', text: error instanceof Error ? error.message : 'That did not work. Please try again.' })
  const send = async (text: string, clientId: string) => {
    setSending(true)
    try {
      const result = await api<{ connection: string }>(`/groups/${id}/messages?wait=false`, { text, client_id: clientId })
      setNotice(result.connection === 'not_configured' ? { tone: 'info', text: 'Your message is saved. Connect a model in Settings so they can reply.', settings: true } : null)
      return true
    } catch (error) { fail(error); return false } finally { setSending(false); await refresh() }
  }
  const act: Change = async (request) => {
    try { await request(); setNotice(null) } catch (error) { fail(error) } finally { await refresh() }
  }
  return { chat, sending, notice, send, act }
}

/** One group chat: the same message markup as the 1:1 chat, so every chat style lays it out. */
export function GroupChat({ id, go }: { id: string; go: (view: View) => void }) {
  const state = useGroupChat(id)
  if (state.chat.isPending) return <Loading label="Opening the group" />
  if (state.chat.isError) return <GroupError error={state.chat.error} go={go} />
  return <GroupChatView data={state.chat.data} state={state} go={go} />
}

function GroupChatView({ data, state, go }: { data: GroupChatData; state: ReturnType<typeof useGroupChat>; go: (view: View) => void }) {
  const { sending, notice, send, act } = state
  const { group } = data
  const id = group.id
  const style = useChatStyle()
  const draft = useDraft(`companion:group-draft:${id}`)
  const ooc = useOoc()
  const shown = shownMessages(data.messages, data.live)
  const { transcript, pinned, follow } = useFollow(shown)
  const scroll = useScrollAway(transcript, pinned)
  const submit = async () => {
    const { clientId } = draft.value
    const text = ooc(draft.value.text)
    if (!text.trim()) { draft.clear(); return }
    draft.setSending(true)
    if (await send(text, clientId)) { draft.clear(); follow() }
    draft.setSending(false)
  }
  // What the members said, once finished, counts as read while the chat is on screen (chats.py group_chats).
  const said = data.messages.filter((message) => message.kind === 'companion' && message.status === 'complete')
  useMarkRead(id, said.length ? Math.max(...said.map((message) => message.seq)) : null)
  return (
    <div className={`chat-shell shell-${style.style}`}>
    <ChatSidebar style={style.style} retroDark={style.retroDark} go={go} current={{ kind: 'group', id }} />
    <section className={`conversation group-chat chat-${style.style}${style.retroDark ? ' retro-dark' : ''}`} aria-label={`Group chat: ${group.title}`}>
      <GroupHeader group={group} go={go} onChange={act} />
      <div className="transcript" ref={transcript} onScroll={scroll.onScroll} role="log" aria-label="Messages" aria-live="off" tabIndex={0}>
        <div className="reading-column">
          {shown.map((message) => <Fragment key={message.id}>
            <GroupLine message={message} onKeep={(kept) => void act(() => api(`/groups/${id}/messages/${message.id}/moment`, { kept }))} />
            {message.crisis_help && <CrisisNote />}
          </Fragment>)}
          <TryAgain shown={canRetry(data)} onRetry={() => void act(() => api(`/groups/${id}/retry?wait=false`, {}))} />
        </div>
        {scroll.away && <div className="jump-latest"><button type="button" className="icon-button" aria-label="Jump to the newest messages" onClick={scroll.toLatest}><ArrowDown aria-hidden="true" /></button></div>}
      </div>
      <p className="chat-activity subtle" role="status" aria-live="polite">{groupActivity(data, sending)}</p>
      <GroupNotice notice={notice ?? (data.ready ? null : NO_MODEL)} go={go} />
      {group.members.length
        ? <Composer name={group.title} draft={draft} streaming={data.busy} compact={scroll.away} onSend={() => void submit()} pictures={false}
          onStop={() => void act(() => api(`/groups/${id}/stop`, {}))} />
        : <GroupNotice notice={NOBODY} go={go} />}
    </section>
    </div>
  )
}

const NO_MODEL: Notice = { tone: 'info', text: 'Connect a model in Settings so they can reply.', settings: true }
const NOBODY: Notice = { tone: 'info', text: 'Add someone to this group to keep talking.' }

/** Keep the newest text in view only while the reader is already at the bottom. */
function useFollow(shown: GroupMessage[]) {
  const transcript = useRef<HTMLDivElement>(null)
  const pinned = useRef(true)
  const lastText = shown.at(-1)?.text
  useEffect(() => {
    const element = transcript.current
    if (element && pinned.current) element.scrollTop = element.scrollHeight
  }, [shown.length, lastText])
  // After sending, the chat follows the replies again.
  const follow = () => { pinned.current = true }
  return { transcript, pinned, follow }
}

function TryAgain({ shown, onRetry }: { shown: boolean; onRetry: () => void }) {
  if (!shown) return null
  return <div className="turn-actions"><button type="button" className="text-button" onClick={onRetry}><RotateCcw aria-hidden="true" />Try again</button></div>
}

function GroupError({ error, go }: { error: Error; go: (view: View) => void }) {
  if (error instanceof ApiError && error.status === 404) {
    return <Notice action={<button type="button" className="text-button" onClick={() => go('groups')}>All groups</button>}>That group chat is gone.</Notice>
  }
  return <ErrorNotice error={error} />
}

function GroupNotice({ notice, go }: { notice: Notice; go: (view: View) => void }) {
  if (!notice) return null
  return (
    <div className="conversation-notice">
      <Notice tone={notice.tone} action={notice.settings ? <button type="button" className="text-button" onClick={() => go('settings/models')}>Open Settings</button> : undefined}>{notice.text}</Notice>
    </div>
  )
}

function Paragraphs({ text }: { text: string }) {
  return <>{text.split(/\n{2,}/).map((part, index) => <p key={index}>{part}</p>)}</>
}

/** A message from you or a member, or the app's own line about who joined or left. A member's finished message
 * can be kept as a shared moment, which brings everyone who was there a little closer. */
function GroupLine({ message, onKeep }: { message: GroupMessage; onKeep: (kept: boolean) => void }) {
  if (message.kind === 'app') return <p className="group-note" role="note">{message.text}</p>
  const mine = message.kind === 'user'
  const name = mine ? 'You' : message.name
  const failure = failureText(message)
  if (failure && !message.text) return <p className="reply-status group-failure" role="note">{failure}</p>
  return (
    <article id={`message-${message.id}`} className={`message ${mine ? 'message-user' : 'message-companion'}`} aria-label={name}>
      <span className="avatar" aria-hidden="true">{name.slice(0, 1).toUpperCase()}</span>
      <header>
        <Stamp value={message.created_at} clock className="stamp-lead" />
        <span className="speaker">{name}</span>
        <span className={mine ? 'message-actions' : 'reply-tools'}>
          <Stamp value={message.created_at} />
          {!mine && message.status === 'complete' && <KeepMoment kept={!!message.kept} onKeep={onKeep} />}
        </span>
      </header>
      <div className="prose"><Paragraphs text={message.text} /></div>
      {failure && <p className="reply-status" role="note">{failure}</p>}
      <SlipNote message={message} />
    </article>
  )
}

/** "Let a secret slip", unless turned off in Settings > General; the secret is out either way. */
function SlipNote({ message }: { message: GroupMessage }) {
  const shown = useWorkspaceSettings().data?.show_secret_slips !== false
  const slip = guardNote(message)
  return shown && slip ? <p className="reply-status group-slip" role="note">{slip}</p> : null
}

function KeepMoment({ kept, onKeep }: { kept: boolean; onKeep: (kept: boolean) => void }) {
  const label = kept ? 'Kept as a shared moment' : 'Keep as a shared moment'
  return (
    <button type="button" className={`text-button${kept ? ' kept' : ''}`} aria-pressed={kept} aria-label={label} title={label} onClick={() => onKeep(!kept)}>
      <HeartHandshake aria-hidden="true" />
    </button>
  )
}

function GroupHeader({ group, go, onChange }: { group: Group; go: (view: View) => void; onChange: Change }) {
  const [renaming, setRenaming] = useState(false)
  const [people, setPeople] = useState(false)
  const [listing, setListing] = useState(false)
  const peopleButton = useReturnFocus<HTMLButtonElement>(people)
  const chatsButton = useReturnFocus<HTMLButtonElement>(listing)
  const current = { kind: 'group', id: group.id }
  return <>
    <header className="conversation-header">
      <button type="button" className="icon-button" aria-label="All groups" onClick={() => go('groups')}><ChevronLeft aria-hidden="true" /></button>
      <div className="portrait" aria-hidden="true"><UsersRound /></div>
      <div className="conversation-title">
        {renaming ? <Rename group={group} onDone={() => setRenaming(false)} onChange={onChange} />
          : <h1>{group.title} <button type="button" className="icon-button group-rename" aria-label="Rename the group" onClick={() => setRenaming(true)}><Pencil aria-hidden="true" /></button></h1>}
        <p className="subtle">{membersLine(group)}</p>
      </div>
      <ChatsButton listing={listing} button={chatsButton} onChats={() => setListing(!listing)} current={current} />
      <ChatStyleSwitch />
      <button ref={peopleButton} type="button" className="icon-button" aria-label="People in this group" aria-expanded={people} onClick={() => setPeople(!people)}><UsersRound aria-hidden="true" /></button>
    </header>
    {people && <GroupPeople group={group} go={go} onChange={onChange} onClose={() => setPeople(false)} />}
    {listing && <ChatsPanel go={go} onClose={() => setListing(false)} current={current} />}
  </>
}

function Rename({ group, onDone, onChange }: { group: Group; onDone: () => void; onChange: Change }) {
  const [name, setName] = useState(group.name)
  const save = () => void onChange(() => api(`/groups/${group.id}`, { name: name.trim() }, 'PATCH')).then(onDone)
  return (
    <form className="group-rename-form" onSubmit={(event) => { event.preventDefault(); save() }}>
      <label className="visually-hidden" htmlFor="group-name">Group name</label>
      <input id="group-name" autoFocus value={name} maxLength={60} placeholder="No name: shows who is in it" onChange={(event) => setName(event.target.value)}
        onKeyDown={(event) => { if (event.key === 'Escape') onDone() }} />
      <button type="submit" className="button primary">Save</button>
      <button type="button" className="text-button" onClick={onDone}>Cancel</button>
    </form>
  )
}

/** Who is in the group: remove someone, add someone (from now on, or with everything so far), and the group's own settings. */
function GroupPeople({ group, go, onChange, onClose }: { group: Group; go: (view: View) => void; onChange: Change; onClose: () => void }) {
  const cast = useCast()
  const [removing, setRemoving] = useState<GroupMember | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [copying, setCopying] = useState(false)
  const inside = group.members.flatMap((member) => member.companion_id ? [member.companion_id] : [])
  return (
    <div className="group-people" role="region" aria-label="People in this group">
      <ul>
        {group.members.map((member) => (
          <li key={member.companion_id ?? member.label}>
            <span>{member.name}{member.main && <span className="subtle"> · main character</span>}<MoodLine mood={member.mood} /></span>
            <button type="button" className="text-button" onClick={() => setRemoving(member)}>Remove from group</button>
          </li>
        ))}
      </ul>
      <AddSomeone group={group} outside={(cast.data?.members ?? []).filter((member) => !inside.includes(member.id))} onChange={onChange} />
      <label className="group-cap">Replies to each message
        <select value={group.reply_cap} onChange={(event) => void onChange(() => api(`/groups/${group.id}`, { reply_cap: Number(event.target.value) }, 'PATCH'))}>
          {[1, 2, 3].map((count) => <option key={count} value={count}>Up to {count}</option>)}
        </select>
      </label>
      <p className="subtle">Anyone you name answers first.</p>
      <label className="group-walk-out"><input type="checkbox" checked={group.walk_out ?? false} onChange={(event) => void onChange(() => api(`/groups/${group.id}`, { walk_out: event.target.checked }, 'PATCH'))} /> People can walk out</label>
      <p className="subtle">When someone stays furious with someone here, they leave the group. You can add them back once they calm down.</p>
      <div className="form-actions">
        <button type="button" className="text-button" onClick={() => setCopying(true)}>New group with these people</button>
        <button type="button" className="text-button danger" onClick={() => setDeleting(true)}>Delete this group…</button>
        <button type="button" className="text-button" onClick={onClose}>Done</button>
      </div>
      {removing && <RemoveDialog group={group} member={removing} onChange={onChange} onClose={() => setRemoving(null)} />}
      {deleting && <DeleteDialog group={group} go={go} onClose={() => setDeleting(false)} />}
      {copying && <NewGroup companions={cast.data?.members ?? []} chosen={inside} onClose={() => setCopying(false)}
        onMade={(made) => { setCopying(false); go(`group/${made.id}`) }} />}
    </div>
  )
}

/** How someone seems right now, read-only, with why (companion/moods.py). Nothing while they seem calm. */
function MoodLine({ mood }: { mood?: GroupMood | null }) {
  if (!mood || mood.feeling === 'calm') return null
  const why = mood.reason ? `: ${mood.reason}` : ''
  return <span className="group-mood subtle"> · {mood.text}{why}{mood.ignoring ? `. Not speaking to ${mood.ignoring}.` : ''}</span>
}

function AddSomeone({ group, outside, onChange }: { group: Group; outside: CastMember[]; onChange: Change }) {
  const [adding, setAdding] = useState('')
  const [everything, setEverything] = useState(false)
  const [ties, setTies] = useState<Backstory[]>([])
  if (!outside.length) return null
  const chosen = outside.some((member) => member.id === adding) ? adding : outside[0].id
  const inside = group.members.flatMap((member) => member.companion_id ? [member.companion_id] : [])
  const told = toldOnly(ties).filter((item) => item.a === chosen || item.b === chosen)
  const add = () => void onChange(() => api(`/groups/${group.id}/members`, { companion_id: chosen, history: everything ? 'everything' : 'from_now', ties: told }))
    .then(() => { setAdding(''); setEverything(false); setTies([]) })
  return (
    <fieldset className="group-add">
      <legend>Add someone</legend>
      <select aria-label="Who to add" value={chosen} onChange={(event) => setAdding(event.target.value)}>
        {outside.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}
      </select>
      <label><input type="radio" name="group-history" checked={!everything} onChange={() => setEverything(false)} /> They see the chat from now on</label>
      <label><input type="radio" name="group-history" checked={everything} onChange={() => setEverything(true)} /> They see everything so far</label>
      <Backstories companionIds={[chosen, ...inside]} value={ties} onChange={setTies} />
      <button type="button" className="button" onClick={add}>Add</button>
    </fieldset>
  )
}

function RemoveDialog({ group, member, onChange, onClose }: { group: Group; member: GroupMember; onChange: Change; onClose: () => void }) {
  return (
    <ConfirmDialog title={`Remove ${member.label}?`} onClose={onClose} actions={<>
      <button type="button" className="button" onClick={onClose}>Cancel</button>
      <button type="button" className="button primary" onClick={() => void onChange(() => api(`/groups/${group.id}/members/${member.companion_id}`, undefined, 'DELETE')).then(onClose)}>Remove</button>
    </>}>
      <p>{member.label} stops getting messages from this group. What {member.label} already heard here stays known: people don&apos;t unlearn a conversation.</p>
    </ConfirmDialog>
  )
}

function DeleteDialog({ group, go, onClose }: { group: Group; go: (view: View) => void; onClose: () => void }) {
  const client = useQueryClient()
  const remove = async () => {
    await api(`/groups/${group.id}`, undefined, 'DELETE')
    await client.invalidateQueries({ queryKey: GROUPS_KEY })
    go('groups')
  }
  return (
    <ConfirmDialog title="Delete this group?" onClose={onClose} actions={<>
      <button type="button" className="button" onClick={onClose}>Cancel</button>
      <button type="button" className="button primary" onClick={() => void remove()}>Delete the group</button>
    </>}>
      <p>The group and its messages are deleted for good. Your 1:1 chats stay as they are.</p>
    </ConfirmDialog>
  )
}
