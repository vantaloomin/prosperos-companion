import { appNow } from '../../appTime.ts'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '../../api'
import type { Companion, DeclineResult, History, Message, RememberResult, SearchResult, SendResult } from '../../types'
import { HISTORY_KEY, MEMORIES_KEY, type View } from '../../companion'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { useReturnFocus } from '../../components/returnFocus'
import { REMEMBER_KEY, rememberedText } from '../memories/memoryGroups'
import { Composer } from './Composer'
import { ConversationHeader } from './ConversationHeader'
import { ConversationSearch } from './ConversationSearch'
import { GettingStarted } from './GettingStarted'
import { releaseHeld, waitsUntilLater } from './held'
import { ActivityLine } from './ActivityLine'
import type { Phase } from './activity'
import { TurnView } from './TurnView'
import { EditDialog, TimelinePanel } from './Timelines'
import { useCurrentTimeline } from './useTimelines'
import { applyFinished, groupTurns, lastUserMessage, liveFor, mergeMessages, replyAnnouncement, streamingIds, turnKey, latestUser } from './turns'
import { useReplyStream } from './useReplyStream'
import { loadBack } from './search'
import { useDraft } from './useDraft'
import { useChatStyle } from './useChatStyle'
import { playCue } from './imSounds'
import { NovelStage } from './NovelStage'
import { latestPhotoId } from './photoState'

const PAGE = 100
const JUMP_PAGE = 500

function ReplyFollower({ id, onText, onPhase, onDone, onLost }: { id: string; onText: (id: string, text: string) => void; onPhase: (id: string, phase: Phase) => void; onDone: (reply: Message) => void; onLost: (id: string) => void }) {
  useReplyStream(id, { onText, onPhase, onDone, onLost })
  return null
}

export function Conversation({ companion, go }: { companion: Companion; go: (view: View) => void }) {
  const client = useQueryClient()
  const history = useQuery({ queryKey: HISTORY_KEY, queryFn: () => api<History>(`/conversation?limit=${PAGE}`) })
  const messages = useMemo(() => history.data?.messages ?? [], [history.data])
  const [live, setLive] = useState<Record<string, string>>({})
  const [phases, setPhases] = useState<Record<string, Phase>>({})
  const [announcement, setAnnouncement] = useState('')
  const [notice, setNotice] = useState<{ tone: 'info' | 'error'; text: string; settings?: boolean } | null>(null)
  const [exhausted, setExhausted] = useState(false)
  const [declining, setDeclining] = useState<Message | null>(null)
  const [editing, setEditing] = useState<Message | null>(null)
  const [found, setFound] = useState<{ id: string; at: number } | null>(null)
  const draft = useDraft()
  const transcript = useRef<HTMLDivElement>(null)
  const pinned = useRef(true)
  const name = companion.version.name
  const chat = useChatStyle()
  const sounds = useRef(chat.sounds)
  useEffect(() => { sounds.current = chat.sounds })

  const timeline = useCurrentTimeline(draft, () => setNotice(null))
  const update = useCallback((change: (messages: Message[]) => Message[]) => {
    client.setQueryData<History>(HISTORY_KEY, (current) => current && { ...current, messages: change(current.messages) })
  }, [client])

  const onText = useCallback((id: string, text: string) => setLive((current) => ({ ...current, [id]: text })), [])
  const onPhase = useCallback((id: string, phase: Phase) => setPhases((current) => ({ ...current, [id]: phase })), [])
  const onDone = useCallback((reply: Message) => {
    if (reply.superseded_at) {
      // The user wrote again before it showed; the reply to their new message takes its place.
      update((current) => current.filter((message) => message.id !== reply.id))
      setLive((current) => { const next = { ...current }; delete next[reply.id]; return next })
      return
    }
    setPhases((current) => { const next = { ...current }; delete next[reply.id]; return next })
    // A reply that shows at once shows the ones held before it; a held one stays quiet until its time.
    // One that failed shows now, so an error is never hidden behind the companion being busy.
    const held = waitsUntilLater(reply, appNow())
    update((current) => applyFinished(held ? current : releaseHeld(current, reply.seq), reply))
    setLive((current) => { const next = { ...current }; delete next[reply.id]; return next })
    if (held) return
    setAnnouncement(replyAnnouncement(name, reply))
    if (sounds.current && reply.status === 'complete') playCue('message')
  }, [update, name])
  const onLost = useCallback(() => { void client.invalidateQueries({ queryKey: HISTORY_KEY }) }, [client])

  // Keep the newest text in view only while the reader is already at the bottom; never pull them away from history.
  useEffect(() => {
    const element = transcript.current
    if (element && pinned.current) element.scrollTop = element.scrollHeight
  }, [messages, live])
  // Bring a search result into view once its page is rendered, and move focus to it for keyboard and screen reader users.
  useEffect(() => {
    const element = found ? document.getElementById(`message-${found.id}`) : null
    if (!element) return
    element.scrollIntoView({ block: 'center' })
    element.focus({ preventScroll: true })
  }, [found])
  const onScroll = () => {
    const element = transcript.current
    if (element) pinned.current = element.scrollHeight - element.scrollTop - element.clientHeight < 80
  }

  const accept = (result: SendResult) => {
    const dropped = new Set(result.dropped ?? [])
    update((current) => mergeMessages(current.filter((message) => !dropped.has(message.id)), [result.message, result.reply, result.follow_up]))
    if (result.connection === 'not_configured') setNotice({ tone: 'info', text: `Your message is saved. Connect a model in Settings so ${name} can reply.`, settings: true })
    else setNotice(null)
    setFound(null)
    pinned.current = true
  }
  const fail = (error: unknown) => setNotice({ tone: 'error', text: error instanceof Error ? error.message : 'That did not work. Please try again.', settings: error instanceof ApiError && error.code === 'not_configured' })

  const send = async () => {
    const { text, clientId, pictures = [] } = draft.value
    if (!text.trim() && !pictures.length) return
    draft.setSending(true)
    try {
      accept(await api<SendResult>('/conversation/messages?wait=false', { text, client_id: clientId, picture_ids: pictures.map((picture) => picture.id) }))
      draft.clear()
    } catch (error) { fail(error) } finally { draft.setSending(false) }
  }
  const retry = async (userId: string) => {
    // The retry button leaves while the new reply is written; the message box is where Escape stops it.
    document.getElementById('composer-text')?.focus()
    try { accept(await api<SendResult>(`/conversation/messages/${userId}/alternatives?wait=false`, {})) } catch (error) { fail(error) }
  }
  const stop = async (replyId: string) => {
    try { await api(`/conversation/replies/${replyId}/stop`, {}) } catch (error) { fail(error) }
  }
  const remember = async (message: Message) => {
    try {
      const result = await api<RememberResult>(`/conversation/messages/${message.id}/remember`, {})
      if (result.memories.length) {
        setNotice({ tone: 'info', text: rememberedText(name, result.memories) })
        void client.invalidateQueries({ queryKey: MEMORIES_KEY })
        return
      }
    } catch (error) { fail(error); return }
    // Nothing recognisable: open the form with the message so the user writes it the way it should be kept.
    try { sessionStorage.setItem(REMEMBER_KEY, JSON.stringify({ messageId: message.id, text: message.text })) } catch { /* The form opens empty. */ }
    go('memories')
  }
  const decline = async (message: Message) => {
    setDeclining(null)
    try {
      const result = await api<DeclineResult>(`/conversation/messages/${message.id}/decline-memory`, {})
      const removed = result.removed_memory_ids.length
      setNotice({ tone: 'info', text: `${name} won't form memories from that message. It stays in your conversation.${removed ? ` ${removed} memor${removed === 1 ? 'y' : 'ies'} saved automatically from it ${removed === 1 ? 'was' : 'were'} removed.` : ''}` })
      if (removed) void client.invalidateQueries({ queryKey: MEMORIES_KEY })
    } catch (error) { fail(error) }
  }
  const loadEarlier = async () => {
    const before = messages[0]?.seq
    try {
      const page = await api<History>(`/conversation?limit=${PAGE}${before ? `&before_seq=${before}` : ''}`)
      update((current) => mergeMessages(current, page.messages))
      setExhausted(page.messages.length < PAGE)
    } catch (error) { fail(error) }
  }

  const jumpTo = async (result: SearchResult) => {
    try {
      const back = await loadBack(messages[0]?.seq, result.seq, JUMP_PAGE,
        async (before) => (await api<History>(`/conversation?limit=${JUMP_PAGE}&before_seq=${before}`)).messages)
      if (back.messages.length) update((current) => mergeMessages(current, back.messages))
      if (back.exhausted) setExhausted(true)
    } catch (error) { fail(error); return false }
    pinned.current = false
    setFound({ id: result.id, at: Date.now() })
    return true
  }

  // Stable handlers and turns, so a streaming reply re-renders its own turn rather than the whole transcript.
  const handlers = useRef({ retry, stop, remember })
  useEffect(() => { handlers.current = { retry, stop, remember } })
  const turnActions = useMemo(() => ({
    retry: (id: string) => void handlers.current.retry(id),
    stop: (id: string) => void handlers.current.stop(id),
    remember: (message: Message) => void handlers.current.remember(message),
    decline: setDeclining,
    edit: setEditing,
  }), [])
  const turns = useMemo(() => groupTurns(messages), [messages])
  const following = streamingIds(messages)
  const latestUserId = latestUser(turns)
  const lastUserId = lastUserMessage(messages)
  // A held reply written in the background stays out of sight: no Stop, and the user can keep writing (pacing.take_over).
  const writing = messages.filter((message) => following.includes(message.id) && !waitsUntilLater(message, appNow())).map((message) => message.id)
  const streaming = writing.length > 0
  const hasEarlier = !exhausted && messages.length >= PAGE

  return (
    <section className={`conversation chat-${chat.style}${chat.retroDark ? ' retro-dark' : ''}`} aria-label={`Conversation with ${name}`}>
      <ConversationTop companion={companion} onJump={jumpTo} timeline={timeline} stage={chat.style === 'novel'} photoId={latestPhotoId(messages)} />
      {following.map((id) => <ReplyFollower key={id} id={id} onText={onText} onPhase={onPhase} onDone={onDone} onLost={onLost} />)}
      <div className="transcript" ref={transcript} onScroll={onScroll} role="log" aria-label="Messages" aria-live="off" tabIndex={0}>
        <div className="reading-column">
          {history.isPending && <Loading label="Loading the conversation" />}
          {history.isError && <ErrorNotice error={history.error} />}
          {hasEarlier && <button type="button" className="text-button load-earlier" onClick={loadEarlier}>Show earlier messages</button>}
          {history.isSuccess && turns.length === 0 && <GettingStarted companion={companion} go={go} />}
          {turns.map((turn) => (
            <TurnView key={turnKey(turn)} turn={turn} name={name} live={liveFor(turn, live)} isLatest={turnKey(turn) === latestUserId} busy={turnKey(turn) === latestUserId && streaming} onRetry={turnActions.retry} onStop={turnActions.stop} onRemember={turnActions.remember} onDecline={turnActions.decline} onEdit={turnActions.edit} bursts={!!companion.version.definition.texting?.bursts} highlight={found?.id} followUpOf={!turn.user && turn === turns.at(-1) ? lastUserId : undefined} />
          ))}
        </div>
      </div>
      <div className="visually-hidden" role="status" aria-live="polite">{announcement}</div>
      <ActivityLine messages={messages} phases={phases} sending={draft.sending} name={name} />
      <ConversationNotice notice={notice} go={go} />
      {editing && <EditDialog message={editing} name={name} onClose={() => setEditing(null)} onDone={() => {
        setEditing(null)
        setNotice({ tone: 'info', text: `You're on the new timeline. Your edited message is in the box below; send it when you're ready.` })
      }} />}
      {declining && <DeclineDialog name={name} onCancel={() => setDeclining(null)} onConfirm={() => void decline(declining)} />}
      <Composer name={name} draft={draft} streaming={streaming} onSend={send} onStop={() => writing.forEach((id) => void stop(id))} />
    </section>
  )
}

function ConversationTop({ companion, onJump, timeline, stage, photoId }: { companion: Companion; onJump: (result: SearchResult) => Promise<boolean>; timeline: string | null; stage: boolean; photoId: string | null }) {
  const [open, setOpen] = useState<'search' | 'timelines' | null>(null)
  const searchButton = useReturnFocus<HTMLButtonElement>(open === 'search')
  const timelinesButton = useReturnFocus<HTMLButtonElement>(open === 'timelines')
  const pick = async (result: SearchResult) => { if (await onJump(result)) setOpen(null) }
  const toggle = (panel: 'search' | 'timelines') => setOpen((current) => current === panel ? null : panel)
  return <>
    <ConversationHeader companion={companion} searching={open === 'search'} searchButton={searchButton} onSearch={() => toggle('search')}
      timeline={timeline} browsing={open === 'timelines'} timelinesButton={timelinesButton} onTimelines={() => toggle('timelines')} />
    {open === 'search' && <ConversationSearch name={companion.version.name} onPick={(result) => void pick(result)} onClose={() => setOpen(null)} />}
    {open === 'timelines' && <TimelinePanel name={companion.version.name} onClose={() => setOpen(null)} />}
    {stage && <NovelStage name={companion.version.name} photoId={photoId} />}
  </>
}

function ConversationNotice({ notice, go }: { notice: { tone: 'info' | 'error'; text: string; settings?: boolean } | null; go: (view: View) => void }) {
  if (!notice) return null
  return (
    <div className="conversation-notice">
      <Notice tone={notice.tone} action={notice.settings ? <button type="button" className="text-button" onClick={() => go('settings/models')}>Open Settings</button> : undefined}>{notice.text}</Notice>
    </div>
  )
}

function DeclineDialog({ name, onCancel, onConfirm }: { name: string; onCancel: () => void; onConfirm: () => void }) {
  return (
    <ConfirmDialog title="Don't remember this message?" onClose={onCancel} actions={<>
      <button type="button" className="button" onClick={onCancel}>Cancel</button>
      <button type="button" className="button primary" onClick={onConfirm}>Don't remember it</button>
    </>}>
      <p>{name} won't turn this message into a memory, now or later. The message itself stays in your conversation.</p>
    </ConfirmDialog>
  )
}
