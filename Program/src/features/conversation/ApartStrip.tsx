import { useQuery } from '@tanstack/react-query'
import { CloudRain, HeartCrack } from 'lucide-react'
import { api } from '../../api'
import { BREAKUP_KEY, breakupStrip, type BreakupView } from '../character/breakupText'

/** Breaks and breakups (companion/life/breakups.py) above the composer, in every chat style: things strained, them
 * thinking about a break, a break, and for a week after it ended, the breakup. A quiet line with no buttons; the
 * Character page says more. */
export function ApartStrip({ name }: { name: string }) {
  const query = useQuery({ queryKey: BREAKUP_KEY, queryFn: () => api<BreakupView>('/life/breakup'), refetchInterval: 300_000 })
  const line = breakupStrip(query.data, name)
  if (!line) return null
  const Glyph = query.data?.stage === 'ended' ? HeartCrack : CloudRain
  return (
    <aside className="where-strip apart-strip" aria-label="Between you" aria-live="polite">
      <Glyph aria-hidden="true" />
      <span>{line}</span>
    </aside>
  )
}
