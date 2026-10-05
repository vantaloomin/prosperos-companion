import { memo, useState, type ReactNode } from 'react'
import { BookmarkPlus, BookmarkX, ChevronLeft, ChevronRight, GitBranch, RotateCcw, Square } from 'lucide-react'
import type { Message } from '../../types'
import { ChatPhoto } from './ChatPhoto'
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
  /** A message found by search: shown even when it is not the default attempt, and marked. */
  highlight?: string | null
}

function Paragraphs({ text }: { text: string }) {
  return <>{text.split(/\n{2,}/).map((part, index) => <p key={index}>{part}</p>)}</>
}

/** Memoized: while a reply streams, only the turn it belongs to re-renders, however long the transcript. */
export const TurnView = memo(function TurnView({ turn, name, live, isLatest, busy, onRetry, onStop, onRemember, onDecline, onEdit, highlight }: Props) {
  const [chosen, setChosen] = useState<string | null>(null)
  const shown = shownAttempt(turn, isLatest, chosen, highlight)
  const index = shown ? turn.attempts.indexOf(shown) : -1
  return (
    <>
      <UserMessage message={turn.user} found={highlight === turn.user.id} settled={turn.attempts.map((item) => item.status).join()} onRemember={onRemember} onDecline={onDecline} onEdit={onEdit} />
      {shown && (
        <Reply message={shown} found={highlight === shown.id} name={name} text={live[shown.id] ?? shown.text} position={turn.attempts.length > 1 ? [index, turn.attempts.length] : null}
          onPage={(step) => setChosen(turn.attempts[index + step]?.id ?? null)} onStop={onStop} />
      )}
      {isLatest && !busy && (
        <div className="turn-actions">
          <button type="button" className="text-button" onClick={() => { setChosen(null); onRetry(turn.user.id) }}>
            <RotateCcw aria-hidden="true" />{shown?.status === 'complete' ? 'Another reply' : 'Retry'}
          </button>
        </div>
      )}
    </>
  )
})

function UserMessage({ message, found, settled, onRemember, onDecline, onEdit }: { message: Message; found: boolean; settled: string; onRemember: (message: Message) => void; onDecline: (message: Message) => void; onEdit: (message: Message) => void }) {
  return (
    <article id={`message-${message.id}`} className={classes('message message-user', { found })} aria-label="You" tabIndex={found ? -1 : undefined}>
      <Avatar name="You" />
      <header>
        <span className="speaker">You</span>
        <span className="message-actions">
          {!message.redacted && <>
            <button type="button" className="text-button" onClick={() => onRemember(message)}><BookmarkPlus aria-hidden="true" />Remember this</button>
            <button type="button" className="text-button" onClick={() => onDecline(message)}><BookmarkX aria-hidden="true" />Don't remember this</button>
            <button type="button" className="text-button" onClick={() => onEdit(message)}><GitBranch aria-hidden="true" />Edit from here</button>
          </>}
          <time dateTime={message.created_at}>{formatTime(message.created_at)}</time>
        </span>
      </header>
      <div className="prose">{message.redacted ? <p className="subtle">This message was deleted.</p> : <Paragraphs text={message.text} />}</div>
      <LinkNotes message={message} settled={settled} />
    </article>
  )
}

function Reply({ message, found, name, text, position, onPage, onStop }: { message: Message; found: boolean; name: string; text: string; position: [number, number] | null; onPage: (step: number) => void; onStop: (id: string) => void }) {
  const note = statusDetail(message)
  const streaming = message.status === 'streaming'
  return (
    <article id={`message-${message.id}`} className={classes('message message-companion', { inactive: !message.active, found })} aria-label={name} aria-busy={streaming} tabIndex={found ? -1 : undefined}>
      <Avatar name={name} />
      <header>
        <span className="speaker">{name}</span>
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
      </header>
      <div className="prose">
        {text ? <Paragraphs text={text} /> : streaming ? <p className="typing subtle">{name} is writing…</p> : null}
      </div>
      {message.photo && <ChatPhoto message={message} name={name} />}
      {note && <p className="reply-status" role="note">{note}</p>}
    </article>
  )
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
