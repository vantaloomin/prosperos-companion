import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react'
import { Heart, X } from 'lucide-react'
import type { Dating as DatingData, DatingCard } from '../../types'
import { reducedMotion } from '../../motion'
import { cardHeading } from './datingText'
import { Photo } from './Photo'
import { FLY_MS, answeredText, arrowWay, decide, hintText, pose, type SwipeWay } from './swipe'

/** Answers the card; true once the app took it. */
type Answer = (key: string, like: boolean) => Promise<boolean>

interface DeckProps { data: DatingData; onSwipe: Answer; onPassedAgain: () => void }

/** The deck: on a dating app a stack of cards to drag left or right; older eras show one notice at a time.
 * Pass and Like stay under it, and the arrow keys answer too. */
export function Deck({ data, onSwipe, onPassedAgain }: DeckProps) {
  const [said, setSaid] = useState<{ name: string; way: SwipeWay } | null>(null)
  const card = data.deck[0]
  const answered: Answer = async (key, like) => {
    const name = data.deck.find((item) => item.key === key)?.name ?? ''
    const done = await onSwipe(key, like)
    if (done) setSaid({ name, way: like ? 'like' : 'pass' })
    return done
  }
  const heard = <p className="visually-hidden" role="status">{said ? answeredText(said.name, said.way, card ? cardHeading(card) : null) : ''}</p>
  if (!card) {
    return <div className="dating-empty">{heard}<p className="subtle">{data.words.empty}</p>
      <button type="button" className="text-button" onClick={onPassedAgain}>See people you passed on again</button></div>
  }
  return <>
    {heard}
    {data.surface === 'app'
      ? <Stack key={card.key} data={data} card={card} onSwipe={answered} />
      : <Notice key={card.key} data={data} card={card} onSwipe={answered} />}
  </>
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
    <article className={`dating-card dating-${data.surface}`} role="group" aria-label={data.surface === 'column' ? 'A notice in the personal column' : cardHeading(card)}>
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
  const still = reducedMotion()
  const answer = (way: SwipeWay) => {
    if (flying) return
    measure()
    setFlying(way)
    setDragging(false)
    window.setTimeout(() => void onSwipe(card.key, way === 'like').finally(() => { setFlying(null); setDx(0) }), FLY_MS)
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
  const at = pose(dx, flying, still, size)
  const next = data.deck[1]
  return (
    <div className="dating-deck">
      <div className={`dating-stack${still ? ' still' : ''}`}>
        {next && <div className="dating-card dating-peek" aria-hidden="true" style={{ transform: `translateY(${10 - 10 * at.lift}px) scale(${0.96 + 0.04 * at.lift})` }}>
          <Details card={next} />
        </div>}
        <article ref={top} className={`dating-card dating-app dating-top${dragging ? ' dragging' : ''}`} role="group" aria-label={cardHeading(card)}
          style={{ transform: `translateX(${at.x}px) rotate(${at.rotate}deg)`, opacity: at.opacity }}
          onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={cancel} onLostPointerCapture={() => { if (drag.current) cancel() }}>
          <span className="dating-stamp like" aria-hidden="true" style={{ opacity: at.like }}>{data.words.like}</span>
          <span className="dating-stamp pass" aria-hidden="true" style={{ opacity: at.pass }}>{data.words.pass}</span>
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
  const touch = window.matchMedia('(pointer: coarse)').matches
  return <>
    <div className="form-actions dating-actions">
      <button type="button" className="button" disabled={busy} aria-keyshortcuts="ArrowLeft" onClick={() => onAnswer('pass')}><X aria-hidden="true" />{data.words.pass}</button>
      <button type="button" className="button primary" disabled={busy} aria-keyshortcuts="ArrowRight" onClick={() => onAnswer('like')}><Heart aria-hidden="true" />{data.words.like}</button>
    </div>
    <p className="subtle dating-left">{hintText(data.remaining - 1, touch, hint)}</p>
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
