import { useState } from 'react'
import { BookmarkPlus, BookmarkX, ChevronLeft, ChevronRight, RotateCcw, Square } from 'lucide-react'
import type { Message } from '../../types'
import { shownAttempt, statusNote, type Turn } from './turns'

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
  /** A message found by search: shown even when it is not the default attempt, and marked. */
  highlight?: string | null
}

function Paragraphs({ text }: { text: string }) {
  return <>{text.split(/\n{2,}/).map((part, index) => <p key={index}>{part}</p>)}</>
}

export function TurnView({ turn, name, live, isLatest, busy, onRetry, onStop, onRemember, onDecline, highlight }: Props) {
  const [chosen, setChosen] = useState<string | null>(null)
  const shown = shownAttempt(turn, isLatest, chosen, highlight)
  const index = shown ? turn.attempts.indexOf(shown) : -1
  return (
    <>
      <UserMessage message={turn.user} found={highlight === turn.user.id} onRemember={onRemember} onDecline={onDecline} />
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
}

function UserMessage({ message, found, onRemember, onDecline }: { message: Message; found: boolean; onRemember: (message: Message) => void; onDecline: (message: Message) => void }) {
  return (
    <article id={`message-${message.id}`} className={classes('message message-user', { found })} aria-label="You" tabIndex={found ? -1 : undefined}>
      <header>
        <span className="speaker">You</span>
        <span className="message-actions">
          {!message.redacted && <>
            <button type="button" className="text-button" onClick={() => onRemember(message)}><BookmarkPlus aria-hidden="true" />Remember this</button>
            <button type="button" className="text-button" onClick={() => onDecline(message)}><BookmarkX aria-hidden="true" />Don't remember this</button>
          </>}
          <time dateTime={message.created_at}>{formatTime(message.created_at)}</time>
        </span>
      </header>
      <div className="prose">{message.redacted ? <p className="subtle">This message was deleted.</p> : <Paragraphs text={message.text} />}</div>
    </article>
  )
}

function Reply({ message, found, name, text, position, onPage, onStop }: { message: Message; found: boolean; name: string; text: string; position: [number, number] | null; onPage: (step: number) => void; onStop: (id: string) => void }) {
  const note = statusNote(message)
  const streaming = message.status === 'streaming'
  return (
    <article id={`message-${message.id}`} className={classes('message message-companion', { inactive: !message.active, found })} aria-label={name} aria-busy={streaming} tabIndex={found ? -1 : undefined}>
      <header>
        <span className="speaker">{name}</span>
        <span className="reply-tools">
          {position && (
            <span className="pager" role="group" aria-label="Reply versions">
              <button type="button" className="icon-button" aria-label="Previous version" disabled={position[0] === 0} onClick={() => onPage(-1)}><ChevronLeft aria-hidden="true" /></button>
              <span>{position[0] + 1} of {position[1]}{message.active ? ', current' : ''}</span>
              <button type="button" className="icon-button" aria-label="Next version" disabled={position[0] === position[1] - 1} onClick={() => onPage(1)}><ChevronRight aria-hidden="true" /></button>
            </span>
          )}
          {streaming && <button type="button" className="text-button" onClick={() => onStop(message.id)}><Square aria-hidden="true" />Stop</button>}
        </span>
      </header>
      <div className="prose">
        {text ? <Paragraphs text={text} /> : streaming ? <p className="typing subtle">{name} is writing…</p> : null}
      </div>
      {note && <p className="reply-status" role="note">{note}{message.error && message.error !== 'Stopped.' ? ` ${message.error}` : ''}</p>}
    </article>
  )
}

function classes(base: string, flags: Record<string, boolean>) {
  return [base, ...Object.keys(flags).filter((flag) => flags[flag])].join(' ')
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }).format(new Date(value))
}
