import { useEffect, useState, type RefObject } from 'react'
import { GitBranch, Search } from 'lucide-react'
import type { ChatStyle, Companion } from '../../types'
import { CHAT_STYLES } from './chatStyles'
import { useChatStyle } from './useChatStyle'
import { usePortrait } from './portrait'

function localTime(timezone: string, now: Date) {
  try {
    return new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit', weekday: 'short', timeZone: timezone }).format(now)
  } catch { return null }
}

type Props = { companion: Companion; searching: boolean; searchButton: RefObject<HTMLButtonElement | null>; onSearch: () => void; timeline: string | null; browsing: boolean; timelinesButton: RefObject<HTMLButtonElement | null>; onTimelines: () => void }

export function ConversationHeader({ companion, searching, searchButton, onSearch, timeline, browsing, timelinesButton, onTimelines }: Props) {
  const { name, timezone, location } = { ...companion.version.definition, name: companion.version.name }
  const [now, setNow] = useState(() => new Date())
  useEffect(() => { const timer = window.setInterval(() => setNow(new Date()), 30_000); return () => window.clearInterval(timer) }, [])
  const time = localTime(timezone, now)
  const portrait = usePortrait()
  return (
    <header className="conversation-header">
      {portrait ? <img className="portrait" src={portrait} alt="" aria-hidden="true" /> : <div className="portrait" aria-hidden="true">{name.slice(0, 1).toUpperCase()}</div>}
      <div className="conversation-title">
        <h1>{name}</h1>
        <p className="subtle">{[timeline, time && `${time} for ${name}`, location].filter(Boolean).join(' · ')}</p>
      </div>
      <ChatStyleSwitch />
      <button ref={timelinesButton} type="button" className="icon-button" aria-label="Timelines" aria-expanded={browsing} onClick={onTimelines}><GitBranch aria-hidden="true" /></button>
      <button ref={searchButton} type="button" className="icon-button" aria-label="Search messages" aria-expanded={searching} onClick={onSearch}><Search aria-hidden="true" /></button>
    </header>
  )
}

/** The quick switch; Settings has the same choice with a description of each style and the sounds option. */
function ChatStyleSwitch() {
  const chat = useChatStyle()
  return (
    <select className="chat-style-switch" aria-label="Chat style" value={chat.style} onChange={(event) => void chat.save({ chat_style: event.target.value as ChatStyle })}>
      {CHAT_STYLES.map((style) => <option key={style.id} value={style.id}>{style.label}</option>)}
    </select>
  )
}
