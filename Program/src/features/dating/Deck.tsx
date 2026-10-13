import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react'
import { Heart, X } from 'lucide-react'
import type { Dating as DatingData, DatingCard } from '../../types'
import { reducedMotion } from '../../motion'
import { cardHeading } from './datingText'
import { Photo } from './Photo'
import { FLY_MS, arrowWay, decide, stamp, threshold, tilt, type SwipeWay } from './swipe'

type Answer = (key: string, like: boolean) => Promise<void>

interface DeckProps { data: DatingData; onSwipe: Answer; onPassedAgain: () => void }

/** The deck: on a dating app a stack of cards to drag left or right; older eras show one notice at a time.
 * Pass and Like stay under it, and the arrow keys answer too. */
export function Deck({ data, onSwipe, onPassedAgain }: DeckProps) {
  const card = data.deck[0]
  if (!card) {
    return <div className="dating-empty"><p className="subtle">{data.words.empty}</p>
      <button type="button" className="text-button" onClick={onPassedAgain}>See people you passed on again</button></div>
  }
  return data.surface === 'app'
    ? <Stack key={card.key} data={data} card={card} onSwipe={onSwipe} />
    : <Notice key={card.key} data={data} card={card} onSwipe={onSwipe} />
}

interface CardProps { data: DatingData; card: DatingCard; onSwipe: Answer }

/** The personal column or the matchmaker: no dragging a newspaper, just the answers and the arrow keys. */
function Notice({ data, card, onSwipe }: CardProps) {
  const [busy, setBusy] = useState(false)
  const answer = (way: SwipeWay) => {
    if (busy) return
    setBusy(true)
    void onSwipe(card.key, way === 'like').finally(() => setBusy(false))
  }
  useArrowKeys(answer)
  return (
    <article className={`dating-card dating-${data.surface}`} aria-label={data.surface === 'column' ? 'A notice in the personal column' : cardHeading(card)}>
      {data.surface === 'column' ? <p className="dating-notice">{card.notice}</p> : <Details card={card} />}
      <Answers data={data} busy={busy} onAnswer={answer} />
    </article>
  )
}

interface Drag { x: number; y: number; at: number; lastX: number; lastAt: number; id: number }

/** One card on top with the next peeking behind. Drag or flick it away and it tilts and fades with a Like or Pass
 * stamp; let go early and it springs back. Text first: a photo shows only if one was already made. */
function Stack({ data, card, onSwipe }: CardProps) {
  const [dx, setDx] = useState(0)
  const [dragging, setDragging] = useState(false)
  const [flying, setFlying] = useState<SwipeWay | null>(null)
  const drag = useRef<Drag | null>(null)
  const top = useRef<HTMLElement>(null)
  const [size, setSize] = useState(360)
  const measure = () => { const width = top.current?.offsetWidth ?? size; setSize(width); return width }
  const answer = (way: SwipeWay) => {
    if (flying) return
    measure()
    setFlying(way)
    setDragging(false)
    const send = () => void onSwipe(card.key, way === 'like').finally(() => { setFlying(null); setDx(0) })
    if (reducedMotion()) send()
    else window.setTimeout(send, FLY_MS)
  }
  useArrowKeys(answer)
  const down = (event: ReactPointerEvent<HTMLElement>) => {
    if (flying || event.button !== 0 || (event.target as HTMLElement).closest('button, a, input, select, textarea')) return
    event.currentTarget.setPointerCapture(event.pointerId)
    measure()
    drag.current = { x: event.clientX, y: event.clientY, at: event.timeStamp, lastX: event.clientX, lastAt: event.timeStamp, id: event.pointerId }
    setDragging(true)
  }
  const move = (event: ReactPointerEvent<HTMLElement>) => {
    const start = drag.current
    if (!start || start.id !== event.pointerId) return
    setDx(event.clientX - start.x)
    drag.current = { ...start, lastX: event.clientX, lastAt: event.timeStamp }
  }
  const up = (event: ReactPointerEvent<HTMLElement>) => {
    const start = drag.current
    drag.current = null
    if (!start || start.id !== event.pointerId) return
    const moved = event.clientX - start.x
    const velocity = (event.clientX - start.lastX) / Math.max(event.timeStamp - start.lastAt, 1) || moved / Math.max(event.timeStamp - start.at, 1)
    const way = decide(moved, velocity, measure())
    if (way) answer(way)
    else { setDragging(false); setDx(0) }
  }
  const cancel = () => { drag.current = null; setDragging(false); setDx(0) }
  const shown = flying ? (flying === 'like' ? 1 : -1) * size * 1.5 : dx
  const marks = flying ? { like: flying === 'like' ? 1 : 0, pass: flying === 'pass' ? 1 : 0 } : stamp(dx, size)
  const lift = Math.min(1, Math.abs(shown) / threshold(size))
  const next = data.deck[1]
  return (
    <div className="dating-deck">
      <div className="dating-stack">
        {next && <div className="dating-card dating-peek" aria-hidden="true" style={{ transform: `translateY(${10 - 10 * lift}px) scale(${0.96 + 0.04 * lift})` }}>
          <Details card={next} />
        </div>}
        <article ref={top} className={`dating-card dating-app dating-top${dragging ? ' dragging' : ''}`} aria-label={cardHeading(card)}
          style={{ transform: `translateX(${shown}px) rotate(${tilt(shown, size)}deg)`, opacity: flying ? 0 : 1 }}
          onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={cancel} onLostPointerCapture={() => { if (drag.current) cancel() }}>
          <span className="dating-stamp like" aria-hidden="true" style={{ opacity: marks.like }}>{data.words.like}</span>
          <span className="dating-stamp pass" aria-hidden="true" style={{ opacity: marks.pass }}>{data.words.pass}</span>
          {data.photos && <Photo key={card.key} personKey={card.key} name={card.name} />}
          <Details card={card} />
        </article>
      </div>
      <Answers data={data} busy={flying !== null} onAnswer={answer} hint />
    </div>
  )
}

function Details({ card }: { card: DatingCard }) {
  return <>
    <h2>{cardHeading(card)}</h2>
    {card.job && <p>{card.job} · {card.neighborhood}</p>}
    <p className="subtle">{card.looks}</p>
    <p>{card.bio}</p>
    <p className="subtle">Looking for {card.looking_text}.</p>
  </>
}

function Answers({ data, busy, onAnswer, hint = false }: { data: DatingData; busy: boolean; onAnswer: (way: SwipeWay) => void; hint?: boolean }) {
  const left = data.remaining - 1
  return <>
    <div className="form-actions dating-actions">
      <button type="button" className="button" disabled={busy} aria-keyshortcuts="ArrowLeft" onClick={() => onAnswer('pass')}><X aria-hidden="true" />{data.words.pass}</button>
      <button type="button" className="button primary" disabled={busy} aria-keyshortcuts="ArrowRight" onClick={() => onAnswer('like')}><Heart aria-hidden="true" />{data.words.like}</button>
    </div>
    <p className="subtle dating-left">{left > 0 ? `${left} more after this one.` : 'The last one for now.'}{hint && ' Drag the card, or use the arrow keys.'}</p>
  </>
}

/** Left passes and right likes while the deck is on screen, unless a field or a dialog has the keys. */
function useArrowKeys(answer: (way: SwipeWay) => void) {
  const latest = useRef(answer)
  useEffect(() => { latest.current = answer })
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || document.querySelector('dialog[open]')) return
      const way = arrowWay(event.key, event.target as HTMLElement | null)
      if (!way) return
      event.preventDefault()
      latest.current(way)
    }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [])
}
