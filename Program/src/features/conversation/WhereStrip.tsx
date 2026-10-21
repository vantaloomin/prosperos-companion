import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { DoorOpen, EyeOff, Home, Luggage, MapPin, Moon, Phone, PhoneIncoming, PhoneMissed, PhoneOff, Sparkles, Undo2 } from 'lucide-react'
import { api } from '../../api'
import { TOGETHER_KEY } from '../today/outingText'
import { HomeStrip } from './HomeStrip'
import { useWhere } from './useWhere'
import { useEraWords, useMagicCalls } from '../world/useEraWords'
import { say, type EraWords } from '../world/eraWords'
import { WHERE_KEY, callActions, callClock, stripAction, stripLine, type CallAction, type StripAction, type StripLine, type WhereCall, type WhereState } from './whereText'

const ACTION_GLYPHS = { 'Head home': Home, 'Call it a night': Moon, Undo: Undo2 } as Record<string, typeof Home>
const CALL_GLYPHS = { answer: Phone, decline: PhoneOff, end: PhoneOff, call: Phone } as Record<CallAction['action'], typeof Home>
// In a fantasy town a call is a scrying glass or a speaking stone, so no handsets (Iris, 2026-10-21).
const MAGIC_GLYPHS = { answer: Sparkles, decline: EyeOff, end: EyeOff, call: Sparkles } as Record<CallAction['action'], typeof Home>

/**
 * The "where you are" strip above the composer, in every chat style: while they are together (out somewhere, at
 * their place, at yours) where and until when, with Head home, Say goodbye or Not now, and Undo for a minute or two
 * after; on a call, how long with End call, and their call ringing with Answer and Decline; a weekend visit across
 * the distance, who is staying with whom and until when (it ends on its own; Today can call one off before it starts);
 * living together, home together of an evening, or you out (HomeStrip). Nothing while apart.
 */
export function WhereStrip({ name }: { name: string }) {
  const client = useQueryClient()
  const where = useWhere()
  const words = useEraWords()
  const line = stripLine(where.data, name, words)
  const call = where.data?.call
  const refresh = (found?: WhereState) => {
    if (found) client.setQueryData(WHERE_KEY, found)
    void client.invalidateQueries({ queryKey: WHERE_KEY })
    void client.invalidateQueries({ queryKey: ['chats'] })
  }
  if (where.data?.home && !line) return <HomeStrip where={where.data} name={name} onDone={refresh} />
  if (!line || !where.data) return null
  if (call) return <CallStrip call={call} lead={line.lead} short={line.short} tail={line.tail} name={name} words={words} onDone={refresh} />
  if (where.data.visit) return (
    <aside className="where-strip" aria-label="Where you are" aria-live="polite">
      <Luggage aria-hidden="true" />
      <span>{line.lead}{line.tail}</span>
    </aside>
  )
  return <OutingStrip where={where.data} line={line} onDone={refresh} />
}

/** Time together out or at one of your places, with its one button. */
function OutingStrip({ where, line, onDone }: { where: WhereState; line: StripLine; onDone: () => void }) {
  const client = useQueryClient()
  const outing = where.outing
  if (!outing) return null
  const action = stripAction(where)
  const act = async (verb: StripAction['action']) => {
    await api(`/life/outings/${outing.id}/${verb}`, {}).catch(() => undefined)
    void client.invalidateQueries({ queryKey: TOGETHER_KEY })
    onDone()
  }
  const Glyph = where.kind === 'out' && outing.state !== 'done' ? MapPin : Home  // Headed home is always the house.
  return (
    <aside className="where-strip" aria-label="Where you are" aria-live="polite">
      <Glyph aria-hidden="true" />
      <span>{line.lead}{line.place && <a className="where-strip-place" href={`#map/${encodeURIComponent(line.place.id)}`} title="Show on map">{line.place.name}</a>}{line.tail}</span>
      {action && <StripButton action={action} onClick={() => void act(action.action)} />}
    </aside>
  )
}

function StripButton({ action, onClick }: { action: StripAction; onClick: () => void }) {
  const Glyph = ACTION_GLYPHS[action.label] ?? DoorOpen
  return <button type="button" className="text-button" onClick={onClick}><Glyph aria-hidden="true" />{action.label}</button>
}

/** A call on the strip: who and how long, with its buttons. Call back starts a new call (POST /api/life/calls). */
function CallStrip({ call, lead, short, tail, name, words, onDone }: { call: WhereCall; lead: string; short?: string; tail: string; name: string; words: EraWords; onDone: (found?: WhereState) => void }) {
  const magic = useMagicCalls()
  const act = async (verb: CallAction['action']) => {
    const path = verb === 'call' ? '/life/calls' : `/life/calls/${call.id}/${verb}`
    onDone(await api<WhereState>(path, {}).catch(() => undefined))
  }
  return (
    <aside className={`where-strip${call.status === 'ringing' ? ' ringing' : ''}`} aria-label={call.status === 'ringing' ? say(words, 'call_ringing', name) : say(words, 'on_call')}>
      <CallIcon call={call} magic={magic} />
      {/* Only the state is announced; the ticking length sits outside the live region. */}
      <span><span aria-live="polite"><CallLead lead={lead} short={short} />{tail}</span>{call.status === 'on' && call.started_at && <> · <CallLength since={call.started_at} /></>}</span>
      {callActions(call, words).map((item) => {
        const Icon = magic ? MAGIC_GLYPHS[item.action] : CALL_GLYPHS[item.action]
        return <button key={item.action} type="button" className={item.action === 'answer' ? 'button primary call-answer' : `text-button call-${item.action}`} onClick={() => void act(item.action)}><Icon aria-hidden="true" />{item.label}</button>
      })}
    </aside>
  )
}

/** The handset for the call's state, or a glint of magic for every state in a fantasy town (useMagicCalls). */
function CallIcon({ call, magic }: { call: WhereCall; magic: boolean }) {
  if (magic) return <Sparkles aria-hidden="true" />
  if (call.status === 'ringing') return <PhoneIncoming aria-hidden="true" />
  if (call.status === 'on') return <Phone aria-hidden="true" />
  return call.status === 'missed' ? <PhoneMissed aria-hidden="true" /> : <PhoneOff aria-hidden="true" />
}

/** The lead, with a shorter one on the phone where the era has one ("Wren Ashby, in the glass"). */
function CallLead({ lead, short }: { lead: string; short?: string }) {
  if (!short || short === lead) return <>{lead}</>
  return <><span className="desktop-only">{lead}</span><span className="phone-only">{short}</span></>
}

/** How long the call has been on, ticking each second; screen readers are not told every tick. */
function CallLength({ since }: { since: string }) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [])
  return <time className="call-length" aria-hidden="true" dateTime={since}>{callClock(now - Date.parse(since))}</time>
}
