import { memo, useEffect, useState, type ReactNode } from 'react'
import { BookmarkPlus, BookmarkX, ChevronLeft, ChevronRight, Ellipsis, GitBranch, RotateCcw, Square } from 'lucide-react'
import type { Message } from '../../types'
import { ChatPhoto } from './ChatPhoto'
import { isHeld } from './held'
import { LinkNotes } from './LinkNotes'
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
  onEdit: (message: Message) => void
  /** Their texting style sends short bursts: each paragraph is its own bubble. */
  bursts: boolean
  /** A message found by search: shown even when it is not the default attempt, and marked. */
  highlight?: string | null
}

function Paragraphs({ text, bursts = false }: { text: string; bursts?: boolean }) {
  return <>{text.split(/\n{2,}/).map((part, index) => <p key={index} className={bursts ? 'burst' : undefined}>{part}</p>)}</>
}

/** Memoized: while a reply streams, only the turn it belongs to re-renders, however long the transcript. */
export const TurnView = memo(function TurnView({ turn, name, live, isLatest, busy, onRetry, onStop, onRemember, onDecline, onEdit, bursts, highlight }: Props) {
  const [chosen, setChosen] = useState<string | null>(null)
  const shown = shownAttempt(turn, isLatest, chosen, highlight)
  const index = shown ? turn.attempts.indexOf(shown) : -1
  return (
    <>
      <Leads messages={turn.leads} name={name} highlight={highlight} onStop={onStop} bursts={bursts} />
      <TurnUser turn={turn} highlight={highlight} onRemember={onRemember} onDecline={onDecline} onEdit={onEdit} />
      {shown && (
        <Reply message={shown} found={highlight === shown.id} name={name} text={live[shown.id] ?? shown.text} position={turn.attempts.length > 1 ? [index, turn.attempts.length] : null}
          onPage={(step) => setChosen(turn.attempts[index + step]?.id ?? null)} onStop={onStop} bursts={bursts} />
      )}
      {isLatest && !busy && turn.user && <RetryAction label={shown?.status === 'complete' ? 'Another reply' : 'Retry'} onRetry={() => { setChosen(null); onRetry(turn.user!.id) }} />}
    </>
  )
})

function RetryAction({ label, onRetry }: { label: string; onRetry: () => void }) {
  return (
    <div className="turn-actions">
      <button type="button" className="text-button" onClick={onRetry}><RotateCcw aria-hidden="true" />{label}</button>
    </div>
  )
}

/** Messages the companion sent first: shown like replies, with no versions to page through. */
function Leads({ messages, name, highlight, onStop, bursts }: { messages: Message[]; name: string; highlight?: string | null; onStop: (id: string) => void; bursts: boolean }) {
  return <>{messages.map((lead) => <Reply key={lead.id} message={lead} found={highlight === lead.id} name={name} text={lead.text} position={null} onPage={() => undefined} onStop={onStop} bursts={bursts} />)}</>
}

function TurnUser({ turn, highlight, onRemember, onDecline, onEdit }: { turn: Turn; highlight?: string | null; onRemember: (message: Message) => void; onDecline: (message: Message) => void; onEdit: (message: Message) => void }) {
  if (!turn.user) return null
  return <UserMessage message={turn.user} found={highlight === turn.user.id} settled={turn.attempts.map((item) => item.status).join()} onRemember={onRemember} onDecline={onDecline} onEdit={onEdit} />
}

function UserMessage({ message, found, settled, onRemember, onDecline, onEdit }: { message: Message; found: boolean; settled: string; onRemember: (message: Message) => void; onDecline: (message: Message) => void; onEdit: (message: Message) => void }) {
  // On a touch screen the actions wait behind a button, so each message is not followed by a row of them.
  const [open, setOpen] = useState(false)
  return (
    <article id={`message-${message.id}`} className={classes('message message-user', { found })} aria-label="You" tabIndex={found ? -1 : undefined}>
      <Avatar name="You" />
      <header>
        <span className="speaker">You</span>
        <span className={classes('message-actions', { open })}>
          {!message.redacted && <>
            <button type="button" className="text-button message-more" aria-expanded={open} onClick={() => setOpen(!open)}><Ellipsis aria-hidden="true" /><span className="visually-hidden">Message actions</span></button>
            <span className="message-tools">
              <button type="button" className="text-button" onClick={() => onRemember(message)}><BookmarkPlus aria-hidden="true" />Remember this</button>
              <button type="button" className="text-button" onClick={() => onDecline(message)}><BookmarkX aria-hidden="true" />Don't remember this</button>
              <button type="button" className="text-button" onClick={() => onEdit(message)}><GitBranch aria-hidden="true" />Edit from here</button>
            </span>
          </>}
          <time dateTime={message.created_at}>{formatTime(message.created_at)}</time>
        </span>
      </header>
      <div className="prose">{message.redacted ? <p className="subtle">This message was deleted.</p> : <Paragraphs text={message.text} />}</div>
      <LinkNotes message={message} settled={settled} />
    </article>
  )
}

interface ReplyProps { message: Message; found: boolean; name: string; text: string; position: [number, number] | null; onPage: (step: number) => void; onStop: (id: string) => void; bursts: boolean }

function Reply({ message, found, name, text, position, onPage, onStop, bursts }: ReplyProps) {
  const note = statusDetail(message)
  const held = useHeld(message)
  // A reply being written while they are away stays out of sight: no typing dots, no Stop.
  const streaming = message.status === 'streaming' && !held
  // Until they get back to the user there is nothing to see; a holding text they sent meanwhile is its own message.
  if (held) return null
  return (
    <article id={`message-${message.id}`} className={classes('message message-companion', { inactive: !message.active, found })} aria-label={name} aria-busy={streaming} tabIndex={found ? -1 : undefined}>
      <Avatar name={name} />
      <header>
        <span className="speaker">{name}</span>
        <ReplyTools message={message} position={position} streaming={streaming} onPage={onPage} onStop={onStop} />
      </header>
      <ReplyBody text={text} name={name} streaming={streaming} bursts={bursts} />
      <ReplyExtras message={message} name={name} note={note} />
    </article>
  )
}

function ReplyTools({ message, position, streaming, onPage, onStop }: Pick<ReplyProps, 'message' | 'position' | 'onPage' | 'onStop'> & { streaming: boolean }) {
  return (
    <span className="reply-tools">
      <time dateTime={message.created_at}>{formatTime(message.created_at)}</time>
      {position && (
        <span className="pager" role="group" aria-label="Reply versions">
          <PageButton label="Previous version" step={-1} disabled={position[0] === 0} onPage={onPage}><ChevronLeft aria-hidden="true" /></PageButton>
          <span>{position[0] + 1} of {position[1]}{message.active ? ', current' : ''}</span>
          <PageButton label="Next version" step={1} disabled={position[0] === position[1] - 1} onPage={onPage}><ChevronRight aria-hidden="true" /></PageButton>
        </span>
      )}
      {streaming && <button type="button" className="text-button" onClick={() => onStop(message.id)}><Square aria-hidden="true" />Stop</button>}
    </span>
  )
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

function ReplyBody({ text, name, streaming, bursts }: { text: string; name: string; streaming: boolean; bursts: boolean }) {
  return (
    <div className={bursts ? 'prose bursts' : 'prose'}>
      {text ? <Paragraphs text={text} bursts={bursts} /> : streaming ? <p className="typing subtle">{name} is writing…</p> : null}
    </div>
  )
}

/** True until the reply's time comes; re-renders once at that moment. */
function useHeld(message: Message): boolean {
  const [now, setNow] = useState(() => Date.now())
  const held = isHeld(message, now)
  useEffect(() => {
    if (!held) return undefined
    const timer = window.setTimeout(() => setNow(Date.now()), Math.min(Date.parse(message.held_until!) - now + 500, 2 ** 31 - 1))
    return () => window.clearTimeout(timer)
  }, [held, message.held_until, now])
  return held
}

/** Shown by the Community style; the other styles hide it. Decorative, since the article is already named. */
function Avatar({ name }: { name: string }) {
  return <span className="avatar" aria-hidden="true">{name.slice(0, 1).toUpperCase()}</span>
}

/** Marked unavailable rather than disabled at either end, so paging to the first or last version keeps keyboard focus on it. */
function PageButton({ label, step, disabled, onPage, children }: { label: string; step: number; disabled: boolean; onPage: (step: number) => void; children: ReactNode }) {
  return <button type="button" className="icon-button" aria-label={label} aria-disabled={disabled} onClick={() => !disabled && onPage(step)}>{children}</button>
}

function classes(base: string, flags: Record<string, boolean>) {
  return [base, ...Object.keys(flags).filter((flag) => flags[flag])].join(' ')
}

// One formatter for every message: making one per message cost more than the rest of a long transcript's render.
const TIME = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })

function formatTime(value: string) {
  return TIME.format(new Date(value))
}
