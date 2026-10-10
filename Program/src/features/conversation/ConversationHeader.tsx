import type { RefObject } from 'react'
import { GitBranch, MessagesSquare, Search, UsersRound } from 'lucide-react'
import type { ChatStyle, Companion } from '../../types'
import { CHAT_STYLES } from './chatStyles'
import { useChatStyle } from './useChatStyle'
import { usePortrait } from './portrait'
import { useLocalTime } from './clock'
import { useChats } from '../chats/useChats'
import { StatusText } from '../status/StatusLine'
import { badge, chatsButtonLabel, othersUnread, type OpenChat } from '../chats/chatText'

type Props = { companion: Companion; listing: boolean; chatsButton: RefObject<HTMLButtonElement | null>; onChats: () => void; searching: boolean; searchButton: RefObject<HTMLButtonElement | null>; onSearch: () => void; timeline: string | null; browsing: boolean; timelinesButton: RefObject<HTMLButtonElement | null>; onTimelines: () => void; onGroups?: () => void }

export function ConversationHeader({ companion, listing, chatsButton, onChats, searching, searchButton, onSearch, timeline, browsing, timelinesButton, onTimelines, onGroups }: Props) {
  const { name, timezone, location } = { ...companion.version.definition, name: companion.version.name }
  const time = useLocalTime(timezone)
  const portrait = usePortrait()
  return (
    <header className="conversation-header">
      <ChatsButton listing={listing} button={chatsButton} onChats={onChats} />
      {portrait ? <img className="portrait" src={portrait} alt="" aria-hidden="true" /> : <div className="portrait" aria-hidden="true">{name.slice(0, 1).toUpperCase()}</div>}
      <div className="conversation-title">
        <h1>{name}</h1>
        <p className="conversation-status"><StatusText name={name} status={companion.status} /></p>
        <p className="subtle">{[timeline, time && `${time} for ${name}`, location].filter(Boolean).join(' · ')}</p>
      </div>
      <ChatStyleSwitch />
      {onGroups && <button type="button" className="icon-button" aria-label="Group chats: start a new group" title="Group chats" onClick={onGroups}><UsersRound aria-hidden="true" /></button>}
      <button ref={timelinesButton} type="button" className="icon-button" aria-label="Timelines" aria-expanded={browsing} onClick={onTimelines}><GitBranch aria-hidden="true" /></button>
      <button ref={searchButton} type="button" className="icon-button" aria-label="Search messages" aria-expanded={searching} onClick={onSearch}><Search aria-hidden="true" /></button>
    </header>
  )
}

/** The way to the other chats, with how many messages wait there; shown once there is more than one chat. */
export function ChatsButton({ listing, button, onChats, current = null }: { listing: boolean; button: RefObject<HTMLButtonElement | null>; onChats: () => void; current?: OpenChat }) {
  const chats = useChats().data?.chats ?? []
  if (chats.length < 2) return null
  const waiting = othersUnread(chats, current)
  return (
    <button ref={button} type="button" className="icon-button chats-button" aria-label={chatsButtonLabel(waiting)} aria-expanded={listing} onClick={onChats}>
      <MessagesSquare aria-hidden="true" />{waiting > 0 && <span className="unread-badge" aria-hidden="true">{badge(waiting)}</span>}
    </button>
  )
}

/** The quick switch; Settings has the same choice with a description of each style and the sounds option. */
export function ChatStyleSwitch() {
  const chat = useChatStyle()
  return (
    <select className="chat-style-switch" aria-label="Chat style" value={chat.style} onChange={(event) => void chat.save({ chat_style: event.target.value as ChatStyle })}>
      {CHAT_STYLES.map((style) => <option key={style.id} value={style.id}>{style.label}</option>)}
    </select>
  )
}
