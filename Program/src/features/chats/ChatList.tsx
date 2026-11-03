import { useState } from 'react'
import { Home, Luggage, MapPin, Phone, Search, Sparkles, UsersRound } from 'lucide-react'
import type { View } from '../../companion'
import type { Chat } from '../../types'
import { Stamp } from '../../components/Stamp'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { portraitUrl } from '../conversation/portrait'
import { badge, chatLabel, isOpen, matching, preview, type OpenChat } from './chatText'
import { useChats, useOpenChat } from './useChats'
import { whereGlyph } from '../status/statusText'
import { useMagicCalls } from '../world/useEraWords'

/**
 * The phone's Chats screen (ChatsHome): every one-to-one and group chat, the most recent first, the way a messaging
 * app lists them: who, their latest message, when, and how many are unread. Never whether anyone is around.
 * A wide screen has the same list beside the chat (ChatSidebar).
 */
export function ChatList({ go, current = null }: { go: (view: View) => void; current?: OpenChat }) {
  const chats = useChats()
  const { open, busy, error } = useOpenChat(go)
  const [query, setQuery] = useState('')
  const choose = (chat: Chat) => void open(chat, isOpen(chat, current))
  return (
    <div className="search-results">
      <ChatSearch query={query} onQuery={setQuery} />
      {chats.isPending && <Loading label="Loading your chats" />}
      {chats.isError && <ErrorNotice error={chats.error} />}
      {error && <Notice tone="error">{error}</Notice>}
      <ul className="chat-list">
        {matching(chats.data?.chats ?? [], query).map((chat) => (
          <li key={`${chat.kind}:${chat.id}`}>
            <button type="button" className={`chat-row${isOpen(chat, current) ? ' current' : ''}${chat.unread ? ' unread' : ''}`} aria-label={chatLabel(chat, current)}
              aria-current={isOpen(chat, current) ? 'true' : undefined} disabled={busy !== null} onClick={() => choose(chat)}>
              <ChatAvatar chat={chat} />
              <span className="chat-row-text">
                <span className="chat-row-top"><strong>{chat.name}</strong>{chat.last && <Stamp className="chat-row-time" value={chat.last.at} short />}</span>
                <span className="chat-row-preview">{busy === chat.id ? 'Opening…' : preview(chat)}</span>
                <ChatWhere chat={chat} />
              </span>
              {chat.unread > 0 && <span className="unread-badge" aria-hidden="true">{badge(chat.unread)}</span>}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Together or apart in plain words under the preview ("At your place", "Long distance, Lisbon", "On a call", luggage on a weekend visit); nothing while apart nearby. */
export function ChatWhere({ chat }: { chat: Chat }) {
  const text = chat.status?.where?.text
  const magic = useMagicCalls()
  const Glyph = { phone: magic ? Sparkles : Phone, luggage: Luggage, pin: MapPin, home: Home }[whereGlyph(chat.status?.where)]
  return text ? <span className="chat-row-where"><Glyph aria-hidden="true" /><span>{text}</span></span> : null
}

export function ChatAvatar({ chat }: { chat: Chat }) {
  if (chat.kind === 'group') return <span className="portrait" aria-hidden="true"><UsersRound /></span>
  // Every companion shows their own picture; their initial stands in while they have none.
  const portrait = portraitUrl(chat.portrait_reference_id)
  if (portrait) return <img className="portrait" src={portrait} alt="" aria-hidden="true" />
  return <span className="portrait" aria-hidden="true">{chat.name.slice(0, 1).toUpperCase()}</span>
}

/** Search by name, at the top of the list as in every messaging app. */
export function ChatSearch({ query, onQuery }: { query: string; onQuery: (query: string) => void }) {
  return (
    <label className="chat-search"><Search aria-hidden="true" />
      <input type="search" value={query} placeholder="Search" aria-label="Search chats" autoComplete="off" onChange={(event) => onQuery(event.target.value)} />
    </label>
  )
}
