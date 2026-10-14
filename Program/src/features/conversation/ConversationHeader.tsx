import { useState, type RefObject } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, Ellipsis, GitBranch, MessageSquareText, MessagesSquare, Phone, Search, UsersRound } from 'lucide-react'
import { api } from '../../api'
import type { ChatStyle, Companion } from '../../types'
import { CHAT_STYLES } from './chatStyles'
import { useChatStyle } from './useChatStyle'
import { usePortrait } from './portrait'
import { useLocalTime } from './clock'
import { useChats } from '../chats/useChats'
import { StatusText } from '../status/StatusLine'
import { badge, chatsButtonLabel, othersUnread, type OpenChat } from '../chats/chatText'
import { useSidecarOpen, useSidecarWaiting } from '../sidecar/store'
import { toggleSidecar } from '../sidecar/toggle'
import { ExportLinks } from '../chats/ExportLinks'
import { useWhere } from './useWhere'
import { WHERE_KEY, canCall, type WhereState } from './whereText'

type Props = { companion: Companion; listing: boolean; chatsButton: RefObject<HTMLButtonElement | null>; onChats: () => void; searching: boolean; searchButton: RefObject<HTMLButtonElement | null>; onSearch: () => void; timeline: string | null; browsing: boolean; timelinesButton: RefObject<HTMLButtonElement | null>; onTimelines: () => void; onGroups?: () => void; onBack?: () => void }

export function ConversationHeader({ companion, listing, chatsButton, onChats, searching, searchButton, onSearch, timeline, browsing, timelinesButton, onTimelines, onGroups, onBack }: Props) {
  const { name, timezone, location } = { ...companion.version.definition, name: companion.version.name }
  const time = useLocalTime(timezone)
  const portrait = usePortrait()
  return (
    <header className="conversation-header">
      {/* On a phone the way back to the Chats list, as every messaging app has; the side list or Chats button does it on a wide screen. */}
      {onBack && <button type="button" className="icon-button chat-back phone-only" aria-label="Chats" onClick={onBack}><ChevronLeft aria-hidden="true" /></button>}
      <ChatsButton listing={listing} button={chatsButton} onChats={onChats} />
      {portrait ? <img className="portrait" src={portrait} alt="" aria-hidden="true" /> : <div className="portrait" aria-hidden="true">{name.slice(0, 1).toUpperCase()}</div>}
      <div className="conversation-title">
        <h1>{name}</h1>
        <p className="conversation-status"><StatusText name={name} status={companion.status} /></p>
        <p className="subtle desktop-only">{[timeline, time && `${time} for ${name}`, location].filter(Boolean).join(' · ')}</p>
        {/* A phone has room for one line: their time and the neighbourhood. */}
        <p className="subtle phone-only">{[timeline, time, location?.split(',')[0]].filter(Boolean).join(' · ')}</p>
      </div>
      <ChatStyleSwitch />
      <span className="header-break phone-only" aria-hidden="true" />
      <CallButton name={name} />
      {onGroups && <button type="button" className="icon-button" aria-label="Group chats: start a new group" title="Group chats" onClick={onGroups}><UsersRound aria-hidden="true" /></button>}
      <button ref={timelinesButton} type="button" className="icon-button" aria-label="Timelines" aria-expanded={browsing} onClick={onTimelines}><GitBranch aria-hidden="true" /></button>
      <button ref={searchButton} type="button" className="icon-button" aria-label="Search messages" aria-expanded={searching} onClick={onSearch}><Search aria-hidden="true" /></button>
      <SidecarButton />
      <ChatMenu threadId={companion.active_timeline_id} />
    </header>
  )
}

/** Call them (companion/life/calls.py): they pick up when they are free, and the strip above the composer shows the
 * call. Hidden while you are together or a call is on or ringing. */
function CallButton({ name }: { name: string }) {
  const client = useQueryClient()
  const where = useWhere().data
  if (!canCall(where)) return null
  const call = async () => {
    const found = await api<WhereState>('/life/calls', {}).catch(() => undefined)
    if (found) client.setQueryData(WHERE_KEY, found)
    void client.invalidateQueries({ queryKey: WHERE_KEY })
    void client.invalidateQueries({ queryKey: ['chats'] })
  }
  return <button type="button" className="icon-button" aria-label={`Call ${name}`} title={`Call ${name}`} onClick={() => void call()}><Phone aria-hidden="true" /></button>
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

/** On a phone the sidecar has no rail button, so it opens from here as a sheet. The side rail keeps its own. */
function SidecarButton() {
  const open = useSidecarOpen()
  const waiting = useSidecarWaiting()
  return (
    <button type="button" className="icon-button sidecar-button phone-only" aria-label={waiting ? 'Sidecar, something waiting' : 'Sidecar'} aria-pressed={open} onClick={() => toggleSidecar(open)}>
      <MessageSquareText aria-hidden="true" />{waiting && <span className="nav-dot" aria-hidden="true" />}
    </button>
  )
}

/** The quick switch; Settings has the same choice with a description of each style and the sounds option. On a phone
 * it moves behind the header's "More" button (ChatMenu), so the header holds no form controls. */
export function ChatStyleSwitch({ phone = false }: { phone?: boolean }) {
  const chat = useChatStyle()
  return (
    <select className={`chat-style-switch${phone ? '' : ' desktop-only'}`} aria-label="Chat style" value={chat.style} onChange={(event) => void chat.save({ chat_style: event.target.value as ChatStyle })}>
      {CHAT_STYLES.map((style) => <option key={style.id} value={style.id}>{style.label}</option>)}
    </select>
  )
}

/** The overflow ("More") at the end of the header's icon row: exporting the chat on screen, and on a phone the chat style. */
export function ChatMenu({ threadId }: { threadId: string }) {
  const [open, setOpen] = useState(false)
  return (
    <span className="header-menu" onKeyDown={(event) => { if (event.key === 'Escape') setOpen(false) }}>
      <button type="button" className="icon-button" aria-label="More" aria-expanded={open} onClick={() => setOpen(!open)}><Ellipsis aria-hidden="true" /></button>
      {open && <div className="header-menu-panel">
        <label className="phone-only">Chat style<ChatStyleSwitch phone /></label>
        <ExportLinks target={{ kind: 'chat', threadId }} onPick={() => setOpen(false)} />
      </div>}
    </span>
  )
}
