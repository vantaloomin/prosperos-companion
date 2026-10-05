import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { api } from '../../api'
import type { Companion, Today } from '../../types'
import { availabilityShort } from '../today/todayText'

function localTime(timezone: string, now: Date) {
  try {
    return new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit', weekday: 'short', timeZone: timezone }).format(now)
  } catch { return null }
}

export function ConversationHeader({ companion, searching, onSearch }: { companion: Companion; searching: boolean; onSearch: () => void }) {
  const { name, timezone, location } = { ...companion.version.definition, name: companion.version.name }
  const [now, setNow] = useState(() => new Date())
  useEffect(() => { const timer = window.setInterval(() => setNow(new Date()), 30_000); return () => window.clearInterval(timer) }, [])
  const time = localTime(timezone, now)
  // Their routine explains a slow reply; it never blocks sending (PRD C5).
  const today = useQuery({ queryKey: ['today'], queryFn: () => api<Today>('/today'), staleTime: 60_000, refetchInterval: 5 * 60_000 })
  const activity = today.data ? availabilityShort(today.data.availability) : null
  return (
    <header className="conversation-header">
      <div className="portrait" aria-hidden="true">{name.slice(0, 1).toUpperCase()}</div>
      <div className="conversation-title">
        <h1>{name}</h1>
        <p className="subtle">{[activity, time && `${time} for ${name}`, location].filter(Boolean).join(' · ')}</p>
      </div>
      <button type="button" className="icon-button" aria-label="Search messages" aria-expanded={searching} onClick={onSearch}><Search aria-hidden="true" /></button>
    </header>
  )
}
