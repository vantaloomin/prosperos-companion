import { useEffect, useRef, useState, type ReactNode, type RefObject } from 'react'
import { useQuery } from '@tanstack/react-query'
import { MessageCircle } from 'lucide-react'
import { api } from '../../api'
import type { View } from '../../companion'
import type { Today as TodayData } from '../../types'
import { usePortrait } from '../conversation/portrait'
import { useEraWords } from '../world/useEraWords'
import { useChatLook } from '../conversation/useTheirLook'
import { firstName } from '../character/panelText'
import { clearOfNow, daySegments, labelFits, type DaySlot } from './dayStrip'
import { weatherLine } from './todayText'

const HOURS = ['12 AM', '6 AM', '12 PM', '6 PM', '12 AM']

/**
 * Today's Now card (style guide: Today): what they are doing and until when, their time, and their whole day as a
 * 24-hour strip in their time zone with a line at now. Message goes to the chat. A gentle default day says so, with the
 * way to describe their routine.
 */
export function NowCard({ data, name, go, status, children }: { data: TodayData; name: string; go: (view: View) => void; status?: string; children?: ReactNode }) {
  const portrait = usePortrait()
  const card = useRef<HTMLElement>(null)
  const look = useChatLook(card)
  const label = useEraWords().message_button
  const at = (value: string) => new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit', timeZone: data.companion_timezone }).format(new Date(value))
  const { label: doing, until } = data.availability
  const now = doingNow(doing, until, at)
  // Away together the trip is the status line (companion/life/away_together.py), and the sub line says what is
  // happening now rather than repeating it (Iris).
  const line = status ?? (now || 'Free')
  const next = data.routine.next
  const after = status ? (doing?.startsWith('Away') ? null : now) : next && `${next.block.label} from ${at(next.starts_at)}`
  const sub = [`${at(data.now)} their time`, after].filter(Boolean).join(' · ')
  // Their city's weather today and tomorrow (companion/world/skies.py), so "move the picnic?" has a reason.
  const weather = weatherLine(data.day)
  return (
    <section ref={card} className={`now-card${look.className}`} style={look.style} data-their-font={look.font} aria-labelledby="now-heading">
      <div className="now-head">
        {portrait ? <img className="portrait" src={portrait} alt="" aria-hidden="true" /> : <span className="portrait" aria-hidden="true">{name.slice(0, 1).toUpperCase()}</span>}
        <div className="now-text">
          <h2 id="now-heading" className="now-line"><span className="now-name">{firstName(name)}</span><span aria-hidden="true"> · </span><span className="visually-hidden">: </span>{line}</h2>
          <p className="row-sub">{sub}</p>
          {weather.full && <>
            <p className="row-sub now-weather desktop-only">{weather.full}</p>
            <p className="row-sub now-weather phone-only">{weather.short}</p>
          </>}
        </div>
        <button type="button" className="button primary now-message" onClick={() => go('conversation')}><MessageCircle aria-hidden="true" />{label}</button>
      </div>
      <DayStrip timezone={data.companion_timezone} now={data.now} />
      {data.routine.default_schedule && <p className="row-sub">A gentle default day. <button type="button" className="text-button inline" onClick={() => go('character')}>Describe their routine</button></p>}
      {children}
    </section>
  )
}

/** "Asleep until 7:00 AM", or null when they are free. */
function doingNow(doing: string | null | undefined, until: string | null | undefined, at: (value: string) => string): string | null {
  return doing ? `${doing}${until ? ` until ${at(until)}` : ''}` : null
}

/** Their day, midnight to midnight where they live. Each part names itself to a screen reader and on hover, and shows
 * its name only where the whole word fits (never cut off). */
function DayStrip({ timezone, now }: { timezone: string; now: string }) {
  const routine = useQuery({ queryKey: ['routine'], queryFn: () => api<{ today?: DaySlot[] }>('/life/routine') })
  const strip = useRef<HTMLOListElement>(null)
  const width = useWidth(strip)
  const slots = routine.data?.today
  if (!slots?.length) return null
  const day = daySegments(slots, now, timezone)
  return (
    <div className="day-strip-wrap">
      <ol ref={strip} className="day-strip" aria-label="Their day, in their time zone">
        {day.segments.map((segment) => (
          <li key={`${segment.label}-${segment.left}`} className={`day-${segment.kind}`} style={{ left: `${segment.left}%`, width: `${segment.width}%` }} title={segment.label}>
            <span className={labelFits(segment, width) && clearOfNow(segment, width, day.now) ? 'day-label' : 'visually-hidden'}>{segment.label}</span>
          </li>
        ))}
        <li className="day-now" style={{ left: `${day.now}%` }} aria-label="Now" />
      </ol>
      <div className="day-hours" aria-hidden="true">{HOURS.map((hour, index) => <span key={index}>{hour}</span>)}</div>
    </div>
  )
}

/** The strip's width in pixels, kept up to date as the window changes. */
function useWidth(element: RefObject<HTMLElement | null>): number {
  const [width, setWidth] = useState(0)
  useEffect(() => {
    const node = element.current
    if (!node) return
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width))
    observer.observe(node)
    return () => observer.disconnect()
  })
  return width
}
