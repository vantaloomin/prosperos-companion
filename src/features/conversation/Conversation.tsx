import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '../../api'
import type { Companion, DeclineResult, History, Message, RememberResult, SearchResult, SendResult } from '../../types'
import { HISTORY_KEY, MEMORIES_KEY, type View } from '../../companion'
import { Loading, Notice } from '../../components/Feedback'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { REMEMBER_KEY, rememberedText } from '../memories/memoryGroups'
import { Composer } from './Composer'
import { ConversationHeader } from './ConversationHeader'
import { ConversationSearch } from './ConversationSearch'
import { GettingStarted } from './GettingStarted'
import { TurnView } from './TurnView'
import { applyFinished, groupTurns, mergeMessages, streamingIds } from './turns'
import { useReplyStream } from './useReplyStream'
import { useDraft } from './useDraft'

const PAGE = 100
const JUMP_PAGE = 500

/** Load older pages until the message at `seq` is present, so a search result can be shown in place. */
async function loadBack(oldest: number | undefined, seq: number, onPage: (messages: Message[]) => void) {
  while (oldest !== undefined && oldest > seq) {
    const page = await api<History>(`/conversation?limit=${JUMP_PAGE}&before_seq=${oldest}`)
    onPage(page.messages)
    if (page.messages.length === 0) return
    oldest = page.messages[0].seq
  }
}

function ReplyFollower({ id, onText, onDone, onLost }: { id: string; onText: (id: string, text: string) => void; onDone: (reply: Message) => void; onLost: (id: string) => void }) {
  useReplyStream(id, { onText, onDone, onLost })
  return null
}

export function Conversation({ companion, go }: { companion: Companion; go: (view: View) => void }) {
  const client = useQueryClient()
  const history = useQuery({ queryKey: HISTORY_KEY, queryFn: () => api<History>(`/conversation?limit=${PAGE}`) })
  const messages = useMemo(() => history.data?.messages ?? [], [history.data])
  const [live, setLive] = useState<Record<string, string>>({})
  const [announcement, setAnnouncement] = useState('')
  const [notice, setNotice] = useState<{ tone: 'info' | 'error'; text: string; settings?: boolean } | null>(null)
  const [exhausted, setExhausted] = useState(false)
  const [declining, setDeclining] = useState<Message | null>(null)
  const [found, setFound] = useState<{ id: string; at: number } | null>(null)
  const draft = useDraft()
  const transcript = useRef<HTMLDivElement>(null)
  const pinned = useRef(true)
  const name = companion.version.name

  const update = useCallback((change: (messages: Message[]) => Message[]) => {
    client.setQueryData<History>(HISTORY_KEY, (current) => current && { ...current, messages: change(current.messages) })
  }, [client])

  const onText = useCallback((id: string, text: string) => setLive((current) => ({ ...current, [id]: text })), [])
  const onDone = useCallback((reply: Message) => {
    update((current) => applyFinished(current, reply))
    setLive((current) => { const next = { ...current }; delete next[reply.id]; return next })
    setAnnouncement(reply.status === 'complete' ? `${name} replied.` : `The reply ended: ${reply.error ?? reply.status}.`)
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
    update((current) => mergeMessages(current, [result.message, result.reply]))
    if (result.connection === 'not_configured') setNotice({ tone: 'info', text: `Your message is saved. Connect a model in Settings so ${name} can reply.`, settings: true })
    else setNotice(null)
    setFound(null)
    pinned.current = true
  }
  const fail = (error: unknown) => setNotice({ tone: 'error', text: error instanceof Error ? error.message : 'That did not work. Please try again.', settings: error instanceof ApiError && error.code === 'not_configured' })

  const send = async () => {
    const { text, clientId } = draft.value
    if (!text.trim()) return
    draft.setSending(true)
    try {
      accept(await api<SendResult>('/conversation/messages?wait=false', { text, client_id: clientId }))
      draft.clear()
    } catch (error) { fail(error) } finally { draft.setSending(false) }
  }
  const retry = async (userId: string) => {
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
      await loadBack(messages[0]?.seq, result.seq, (page) => {
        update((current) => mergeMessages(current, page))
        if (page.length < JUMP_PAGE) setExhausted(true)
      })
    } catch (error) { fail(error); return false }
    pinned.current = false
    setFound({ id: result.id, at: Date.now() })
    return true
  }

  const turns = groupTurns(messages)
  const following = streamingIds(messages)
  const latestUserId = turns.at(-1)?.user.id
  const streaming = following.length > 0
  const hasEarlier = !exhausted && messages.length >= PAGE

  return (
    <section className="conversation" aria-label={`Conversation with ${name}`}>
      <ConversationTop companion={companion} onJump={jumpTo} />
      {following.map((id) => <ReplyFollower key={id} id={id} onText={onText} onDone={onDone} onLost={onLost} />)}
      <div className="transcript" ref={transcript} onScroll={onScroll} role="log" aria-label="Messages" aria-live="off" tabIndex={0}>
        <div className="reading-column">
          {history.isPending && <Loading label="Loading the conversation" />}
          {history.isError && <Notice tone="error">{history.error.message}</Notice>}
          {hasEarlier && <button type="button" className="text-button load-earlier" onClick={loadEarlier}>Show earlier messages</button>}
          {history.isSuccess && turns.length === 0 && <GettingStarted companion={companion} go={go} />}
          {turns.map((turn) => (
            <TurnView key={turn.user.id} turn={turn} name={name} live={live} isLatest={turn.user.id === latestUserId} busy={streaming} onRetry={retry} onStop={stop} onRemember={remember} onDecline={setDeclining} highlight={found?.id} />
          ))}
        </div>
      </div>
      <div className="visually-hidden" role="status" aria-live="polite">{announcement}</div>
      {notice && <ConversationNotice notice={notice} go={go} />}
      {declining && <DeclineDialog name={name} onCancel={() => setDeclining(null)} onConfirm={() => void decline(declining)} />}
      <Composer name={name} draft={draft} streaming={streaming} onSend={send} onStop={() => following.forEach((id) => void stop(id))} />
    </section>
  )
}

function ConversationTop({ companion, onJump }: { companion: Companion; onJump: (result: SearchResult) => Promise<boolean> }) {
  const [searching, setSearching] = useState(false)
  const pick = async (result: SearchResult) => { if (await onJump(result)) setSearching(false) }
  return <>
    <ConversationHeader companion={companion} searching={searching} onSearch={() => setSearching((open) => !open)} />
    {searching && <ConversationSearch name={companion.version.name} onPick={(result) => void pick(result)} onClose={() => setSearching(false)} />}
  </>
}

function ConversationNotice({ notice, go }: { notice: { tone: 'info' | 'error'; text: string; settings?: boolean }; go: (view: View) => void }) {
  return (
    <div className="conversation-notice">
      <Notice tone={notice.tone} action={notice.settings ? <button type="button" className="text-button" onClick={() => go('settings')}>Open Settings</button> : undefined}>{notice.text}</Notice>
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
