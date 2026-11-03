import type { RefObject } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, GitBranch, Lightbulb, Phone, Search, Sparkles, UsersRound } from 'lucide-react'
import { api } from '../../api'
import type { Companion } from '../../types'
import type { MenuEntry, MenuItem } from '../../components/Menu'
import { usePhone } from '../../components/usePhone'
import { usePortrait } from './portrait'
import { useLocalTime } from './clock'
import { StatusText } from '../status/StatusLine'
import { ListButton } from '../chats/ListButton'
import { useSidecarOpen, useSidecarWaiting } from '../sidecar/store'
import { toggleSidecar } from '../sidecar/toggle'
import { useEraWords, useMagicCalls } from '../world/useEraWords'
import { say } from '../world/eraWords'
import { useWhere } from './useWhere'
import { WHERE_KEY, canCall, type WhereState } from './whereText'
import { ChatMenu } from './ChatMenu'

type Props = { companion: Companion; searching: boolean; searchButton: RefObject<HTMLButtonElement | null>; onSearch: () => void; timeline: string | null; onTimelines: () => void; onGroups?: () => void; onBack?: () => void; onProfile: () => void }

/**
 * The chat's header (style guide: Chat header): the panel button, their picture and name, one status line, then at
 * most four buttons: Call, Search, Sidecar and ⋯. Timelines, Start a group, Export and the chat style live under ⋯,
 * and on a phone Call and Search move there too. Their name (or picture) opens their profile: Posts, Memories, Character.
 */
export function ConversationHeader({ companion, searching, searchButton, onSearch, timeline, onTimelines, onGroups, onBack, onProfile }: Props) {
  const name = companion.version.name
  const portrait = usePortrait()
  const phone = usePhone()
  const call = useCall(name)
  const items: MenuEntry[] = [
    ...(phone ? phoneItems(call, onSearch) : []),
    { label: 'Timelines', icon: GitBranch, onSelect: onTimelines },
    ...(onGroups ? [{ label: `Start a group with ${name}`, icon: UsersRound, onSelect: onGroups }] : []),
  ]
  return (
    <header className="conversation-header">
      {/* On a phone the way back to the Chats list, as every messaging app has; the side list does it on a wide screen. */}
      {onBack && <button type="button" className="icon-button chat-back phone-only" aria-label="Chats" onClick={onBack}><ChevronLeft aria-hidden="true" /></button>}
      <ListButton />
      {/* The picture is a mouse shortcut to the same profile the name opens, so keyboards and screen readers meet it once. */}
      <button type="button" className="portrait-button" tabIndex={-1} aria-hidden="true" onClick={onProfile}>
        {portrait ? <img className="portrait" src={portrait} alt="" /> : <span className="portrait">{name.slice(0, 1).toUpperCase()}</span>}
      </button>
      <div className="conversation-title">
        <h1><button type="button" className="name-button" title="Open profile" onClick={onProfile}>{name}</button></h1>
        <StatusLine companion={companion} timeline={timeline} phone={phone} />
      </div>
      {!phone && <WideButtons call={call} searching={searching} searchButton={searchButton} onSearch={onSearch} />}
      <SidecarButton />
      <ChatMenu threadId={companion.active_timeline_id} items={items} />
    </header>
  )
}

/** On a phone, Call and Search wait under ⋯ so the name keeps its room. */
function phoneItems(call: MenuItem | null, onSearch: () => void): MenuItem[] {
  return [...(call ? [call] : []), { label: 'Search messages', icon: Search, onSelect: onSearch }]
}

function WideButtons({ call, searching, searchButton, onSearch }: { call: MenuItem | null; searching: boolean; searchButton: RefObject<HTMLButtonElement | null>; onSearch: () => void }) {
  const CallIcon = call?.icon ?? Phone
  return <>
    {call && <button type="button" className="icon-button" aria-label={call.label} title={call.label} onClick={call.onSelect}><CallIcon aria-hidden="true" /></button>}
    <button ref={searchButton} type="button" className="icon-button" aria-label="Search messages" title="Search messages" aria-expanded={searching} onClick={onSearch}><Search aria-hidden="true" /></button>
  </>
}

/**
 * One line under the name: what they're up to, their time and the neighbourhood ("just vibing · 2:22 PM their time ·
 * Fells Point"). A phone keeps only the status and the time ("just vibing · 9:51 PM"), and the status gives way first so
 * the time always shows. A side timeline leads, so it is never mistaken for the main one.
 */
function StatusLine({ companion, timeline, phone }: { companion: Companion; timeline: string | null; phone: boolean }) {
  const { timezone, location } = companion.version.definition
  const time = useLocalTime(timezone, phone)
  const when = phone ? time : time && `${time} their time`
  const place = phone ? null : location?.split(',')[0]
  const rest = [timeline, when, place].filter(Boolean).join(' · ')
  return (
    <p className="conversation-status">
      <StatusText name={companion.version.name} status={companion.status} />
      {rest && companion.status?.text && <span className="meta-sep" aria-hidden="true">·</span>}
      {rest && <span className="conversation-meta">{rest}</span>}
    </p>
  )
}

/** Call them (companion/life/calls.py): they pick up when they are free, and the strip above the composer shows the
 * call. Nothing while you are together or a call is on or ringing. */
function useCall(name: string): MenuItem | null {
  const client = useQueryClient()
  const where = useWhere().data
  const label = say(useEraWords(), 'call_to', name)
  const magic = useMagicCalls()
  if (!canCall(where)) return null
  const call = async () => {
    const found = await api<WhereState>('/life/calls', {}).catch(() => undefined)
    if (found) client.setQueryData(WHERE_KEY, found)
    void client.invalidateQueries({ queryKey: WHERE_KEY })
    void client.invalidateQueries({ queryKey: ['chats'] })
  }
  return { label, icon: magic ? Sparkles : Phone, onSelect: () => void call() }
}

/** The sidecar opens beside the chat, on a wide screen as on a phone (it left the side rail in 1.3). */
function SidecarButton() {
  const open = useSidecarOpen()
  const waiting = useSidecarWaiting()
  const label = waiting ? 'Sidecar, something waiting' : 'Sidecar'
  return (
    <button type="button" className="icon-button sidecar-button" aria-label={label} title="Sidecar" aria-pressed={open} onClick={() => toggleSidecar(open)}>
      <Lightbulb aria-hidden="true" />{waiting && <span className="nav-dot" aria-hidden="true" />}
    </button>
  )
}
