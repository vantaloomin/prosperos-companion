import { appNow, realDelay } from '../../appTime.ts'
import { memo, useEffect, useState, type ReactNode } from 'react'
import { BookmarkPlus, BookmarkX, ChevronLeft, ChevronRight, Ellipsis, GitBranch, HeartHandshake, MessageSquareText, Pencil, RotateCcw, Square } from 'lucide-react'
import type { Message } from '../../types'
import { ChatPhoto } from './ChatPhoto'
import { Stamp } from '../../components/Stamp'
import { sidecar } from '../sidecar/store'
import { waitsUntilLater } from './held'
import { LinkNotes } from './LinkNotes'
import { SentPictures } from './SentPictures'
import { usePortrait } from './portrait'
import { shownAttempt, statusDetail, type Turn } from './turns'

interface Props {
  turn: Turn
  name: string
  live: Record<string, string>
  isLatest: boolean
  busy: boolean
  onRetry: (userId: string) => void
  onStop: (replyId: string) => void
  onRemember: (message: Message) => void
  onDecline: (message: Message) => void
  /** Your message: Edit from here (a new timeline). Their reply: new wording in place. */
  onEdit: (message: Message) => void
  /** A new timeline with everything up to and including this message, yours or theirs. */
  onBranch: (message: Message) => void
  /** Keep this message, yours or theirs, as a shared moment (it counts toward closeness). */
  onMoment: (message: Message) => void
  /** Their texting style sends short bursts: each paragraph is its own bubble. */
  bursts: boolean
  /** A message found by search: shown even when it is not the default attempt, and marked. */
  highlight?: string | null
  /** On the newest turn when it holds only the companion's messages: the user message they answer, for Retry. */
  followUpOf?: string
}

function Paragraphs({ text, bursts = false }: { text: string; bursts?: boolean }) {
  return <>{text.split(/\n{2,}/).map((part, index) => <p key={index} className={bursts ? 'burst' : undefined}>{part}</p>)}</>
}

/** Memoized: while a reply streams, only the turn it belongs to re-renders, however long the transcript. */
export const TurnView = memo(function TurnView({ turn, name, live, isLatest, busy, onRetry, onStop, onRemember, onDecline, onEdit, onBranch, onMoment, bursts, highlight, followUpOf }: Props) {
  const [chosen, setChosen] = useState<string | null>(null)
  const shown = shownAttempt(turn, isLatest, chosen, highlight)
  const index = shown ? turn.attempts.indexOf(shown) : -1
  return (
    <>
      <Leads messages={turn.leads} name={name} highlight={highlight} onStop={onStop} onEdit={onEdit} onBranch={onBranch} onMoment={onMoment} bursts={bursts} />
      <TurnUser turn={turn} name={name} highlight={highlight} onRemember={onRemember} onDecline={onDecline} onEdit={onEdit} onBranch={onBranch} onMoment={onMoment} />
      {shown && (
        <Reply message={shown} found={highlight === shown.id} name={name} text={live[shown.id] ?? shown.text} position={turn.attempts.length > 1 ? [index, turn.attempts.length] : null}
          onPage={(step) => setChosen(turn.attempts[index + step]?.id ?? null)} onStop={onStop} onEdit={onEdit} onBranch={onBranch} onMoment={onMoment} bursts={bursts} />
      )}
      {!busy && <TurnRetry turn={turn} isLatest={isLatest} shown={shown} followUpOf={followUpOf} onRetry={(id) => { setChosen(null); onRetry(id) }} />}
    </>
  )
})

/** Another reply or Retry under the newest message, or Retry under a promised full reply that failed. */
function TurnRetry({ turn, isLatest, shown, followUpOf, onRetry }: { turn: Turn; isLatest: boolean; shown: Message | null; followUpOf?: string; onRetry: (userId: string) => void }) {
  if (isLatest && turn.user) return <RetryAction label={shown?.status === 'complete' ? 'Another reply' : 'Retry'} onRetry={() => onRetry(turn.user!.id)} />
  if (followUpOf && failedFollowUp(turn.leads.at(-1))) return <RetryAction label="Retry" onRetry={() => onRetry(followUpOf)} />
  return null
}

/** The full reply promised after a holding text ("brb, boss is here") that failed: it answers the user's last message. */
function failedFollowUp(lead: Message | undefined): boolean {
  return !!lead?.held_line && (lead.status === 'failed' || lead.status === 'incomplete')
}

function RetryAction({ label, onRetry }: { label: string; onRetry: () => void }) {
  return (
    <div className="turn-actions">
      <button type="button" className="text-button" onClick={onRetry}><RotateCcw aria-hidden="true" />{label}</button>
    </div>
  )
}

/** Messages the companion sent first: shown like replies, with no versions to page through. */
type Act = (message: Message) => void

function Leads({ messages, name, highlight, onStop, onEdit, onBranch, onMoment, bursts }: { messages: Message[]; name: string; highlight?: string | null; onStop: (id: string) => void; onEdit: Act; onBranch: Act; onMoment: Act; bursts: boolean }) {
  return <>{messages.map((lead) => <Reply key={lead.id} message={lead} found={highlight === lead.id} name={name} text={lead.text} position={null} onPage={() => undefined} onStop={onStop} onEdit={onEdit} onBranch={onBranch} onMoment={onMoment} bursts={bursts} />)}</>
}

function TurnUser({ turn, name, highlight, onRemember, onDecline, onEdit, onBranch, onMoment }: { turn: Turn; name: string; highlight?: string | null; onRemember: Act; onDecline: Act; onEdit: Act; onBranch: Act; onMoment: Act }) {
  if (!turn.user) return null
  return <UserMessage message={turn.user} name={name} found={highlight === turn.user.id} settled={turn.attempts.map((item) => item.status).join()} onRemember={onRemember} onDecline={onDecline} onEdit={onEdit} onBranch={onBranch} onMoment={onMoment} />
}

/** A message's actions. On a touch screen they wait behind a button, so each message is not followed by a row of them.
 * Opened, they float over the messages below (styles.css) and close once one is used or focus leaves. */
function MessageActions({ message, actions, children }: { message: Message; actions: [string, ReactNode, Act][]; children?: ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <span className={classes('message-actions', { open })}
      onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false) }}
      onKeyDown={(event) => { if (event.key === 'Escape') setOpen(false) }}>
      {actions.length > 0 && <>
        <button type="button" className="text-button message-more" aria-expanded={open} onClick={() => setOpen(!open)}><Ellipsis aria-hidden="true" /><span className="visually-hidden">Message actions</span></button>
        <span className="message-tools">
          {actions.map(([label, icon, action]) => <button key={label} type="button" className="text-button" onClick={() => { setOpen(false); action(message) }}>{icon}{label}</button>)}
        </span>
      </>}
      {children}
    </span>
  )
}

function UserMessage({ message, name, found, settled, onRemember, onDecline, onEdit, onBranch, onMoment }: { message: Message; name: string; found: boolean; settled: string; onRemember: Act; onDecline: Act; onEdit: Act; onBranch: Act; onMoment: Act }) {
  const actions: [string, ReactNode, Act][] = message.redacted ? [] : [
    ['Remember this', <BookmarkPlus key="icon" aria-hidden="true" />, onRemember],
    [MOMENT, <HeartHandshake key="icon" aria-hidden="true" />, onMoment],
    ["Don't remember this", <BookmarkX key="icon" aria-hidden="true" />, onDecline],
    ['Edit', <Pencil key="icon" aria-hidden="true" />, onEdit],
    ['Branch from here', <GitBranch key="icon" aria-hidden="true" />, onBranch],
  ]
  return (
    <article id={`message-${message.id}`} className={classes('message message-user', { found })} aria-label="You" tabIndex={found ? -1 : undefined}>
      <Avatar name="You" />
      <header>
        <Stamp value={message.created_at} clock className="stamp-lead" />
        <span className="speaker">You</span>
        <MessageActions message={message} actions={actions}><Stamp value={message.created_at} /></MessageActions>
      </header>
      <div className="prose">{message.redacted ? <p className="subtle">This message was deleted.</p> : <Paragraphs text={message.text} />}</div>
      {!message.redacted && <SentPictures message={message} name={name} />}
      <LinkNotes message={message} settled={settled} />
    </article>
  )
}

interface ReplyProps { message: Message; found: boolean; name: string; text: string; position: [number, number] | null; onPage: (step: number) => void; onStop: (id: string) => void; onEdit: Act; onBranch: Act; onMoment: Act; bursts: boolean }

function Reply({ message, found, name, text, position, onPage, onStop, onEdit, onBranch, onMoment, bursts }: ReplyProps) {
  const note = statusDetail(message)
  const held = useHeld(message)
  // A reply being written while they are away stays out of sight: no typing dots, no Stop.
  const streaming = message.status === 'streaming' && !held
  // Until they get back to the user there is nothing to see; a holding text they sent meanwhile is its own message.
  if (held) return null
  return (
    <article id={`message-${message.id}`} className={classes('message message-companion', { inactive: !message.active, found })} aria-label={name} aria-busy={streaming} tabIndex={found ? -1 : undefined}>
      <Avatar name={name} companion />
      <header>
        <Stamp value={message.created_at} clock className="stamp-lead" />
        <span className="speaker">{name}</span>
        <ReplyTools message={message} position={position} streaming={streaming} onPage={onPage} onStop={onStop} onEdit={onEdit} onBranch={onBranch} onMoment={onMoment} />
      </header>
      <ReplyBody text={text} streaming={streaming} bursts={bursts} />
      <ReplyExtras message={message} name={name} note={note} />
    </article>
  )
}

function ReplyTools({ message, position, streaming, onPage, onStop, onEdit, onBranch, onMoment }: Pick<ReplyProps, 'message' | 'position' | 'onPage' | 'onStop' | 'onEdit' | 'onBranch' | 'onMoment'> & { streaming: boolean }) {
  const actions = replyActions(message, streaming, onEdit, onBranch, onMoment)
  return (
    <span className="reply-tools">
      <Stamp value={message.created_at} />
      {position && (
        <span className="pager" role="group" aria-label="Reply versions">
          <PageButton label="Previous version" step={-1} disabled={position[0] === 0} onPage={onPage}><ChevronLeft aria-hidden="true" /></PageButton>
          <span>{position[0] + 1} of {position[1]}{message.active ? ', current' : ''}</span>
          <PageButton label="Next version" step={1} disabled={position[0] === position[1] - 1} onPage={onPage}><ChevronRight aria-hidden="true" /></PageButton>
        </span>
      )}
      {streaming && <button type="button" className="text-button" onClick={() => onStop(message.id)}><Square aria-hidden="true" />Stop</button>}
      {message.status === 'complete' && !message.redacted && <button type="button" className="text-button reply-sidecar" aria-label="Ask the sidecar about this reply" title="Ask the sidecar about this reply" onClick={() => sidecar.ask(message)}><MessageSquareText aria-hidden="true" /></button>}
      <MessageActions message={message} actions={actions} />
    </span>
  )
}

const MOMENT = 'Keep as a shared moment'

/** Only a finished reply can be reworded or kept as a shared moment; one that stopped or failed can still be a branch point. */
function replyActions(message: Message, streaming: boolean, onEdit: Act, onBranch: Act, onMoment: Act): [string, ReactNode, Act][] {
  if (message.redacted || streaming || message.status === 'withheld') return []
  const branch: [string, ReactNode, Act] = ['Branch from here', <GitBranch key="icon" aria-hidden="true" />, onBranch]
  return message.status === 'complete'
    ? [['Edit', <Pencil key="icon" aria-hidden="true" />, onEdit], [MOMENT, <HeartHandshake key="icon" aria-hidden="true" />, onMoment], branch]
    : [branch]
}

/** What follows a reply once it shows: the picture it sent and a note on how it ended. */
function ReplyExtras({ message, name, note }: { message: Message; name: string; note: string | null }) {
  return (
    <>
      {message.photo && <ChatPhoto message={message} name={name} />}
      {note && <p className="reply-status" role="note">{note}</p>}
    </>
  )
}

/** Before any text arrives, a quiet placeholder; the line above the message box says what is happening. */
function ReplyBody({ text, streaming, bursts }: { text: string; streaming: boolean; bursts: boolean }) {
  return (
    <div className={bursts ? 'prose bursts' : 'prose'}>
      {text ? <Paragraphs text={text} bursts={bursts} /> : streaming ? <p className="typing subtle" aria-hidden="true">…</p> : null}
    </div>
  )
}

/** True until the reply's time comes; re-renders once at that moment. A failed reply is never held. */
function useHeld(message: Message): boolean {
  const [now, setNow] = useState(() => appNow())
  const held = waitsUntilLater(message, now)
  useEffect(() => {
    if (!held) return undefined
    const timer = window.setTimeout(() => setNow(appNow()), Math.min(realDelay(Date.parse(message.held_until!) - now) + 500, 2 ** 31 - 1))
    return () => window.clearTimeout(timer)
  }, [held, message.held_until, now])
  return held
}

/** Shown by the Community style; the other styles hide it. Decorative, since the article is already named. */
function Avatar({ name, companion = false }: { name: string; companion?: boolean }) {
  const portrait = usePortrait()
  if (companion && portrait) return <img className="avatar" src={portrait} alt="" aria-hidden="true" />
  return <span className="avatar" aria-hidden="true">{name.slice(0, 1).toUpperCase()}</span>
}

/** Marked unavailable rather than disabled at either end, so paging to the first or last version keeps keyboard focus on it. */
function PageButton({ label, step, disabled, onPage, children }: { label: string; step: number; disabled: boolean; onPage: (step: number) => void; children: ReactNode }) {
  return <button type="button" className="icon-button" aria-label={label} aria-disabled={disabled} onClick={() => !disabled && onPage(step)}>{children}</button>
}

function classes(base: string, flags: Record<string, boolean>) {
  return [base, ...Object.keys(flags).filter((flag) => flags[flag])].join(' ')
}
