import { useEffect, useState } from 'react'
import type { Companion } from '../../types'

function localTime(timezone: string, now: Date) {
  try {
    return new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit', weekday: 'short', timeZone: timezone }).format(now)
  } catch { return null }
}

export function ConversationHeader({ companion }: { companion: Companion }) {
  const { name, timezone, location } = { ...companion.version.definition, name: companion.version.name }
  const [now, setNow] = useState(() => new Date())
  useEffect(() => { const timer = window.setInterval(() => setNow(new Date()), 30_000); return () => window.clearInterval(timer) }, [])
  const time = localTime(timezone, now)
  return (
    <header className="conversation-header">
      <div className="portrait" aria-hidden="true">{name.slice(0, 1).toUpperCase()}</div>
      <div>
        <h1>{name}</h1>
        <p className="subtle">{[time && `${time} for ${name}`, location].filter(Boolean).join(' · ')}</p>
      </div>
    </header>
  )
}
