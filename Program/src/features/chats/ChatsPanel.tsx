import { X } from 'lucide-react'
import type { View } from '../../companion'
import type { Chat } from '../../types'
import { Stamp } from '../../components/Stamp'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { usePortrait } from '../conversation/portrait'
import { badge, chatLabel, preview } from './chatText'
import { useChats, useOpenChat } from './useChats'

/**
 * Every chat, the most recent first, the way a messaging app lists them: who, their latest message, when, and
 * how many are unread. Never whether anyone is around. On a phone it covers the screen.
 */
export function ChatsPanel({ go, onClose }: { go: (view: View) => void; onClose: () => void }) {
  const chats = useChats()
  const { open, busy, error } = useOpenChat(go)
  const choose = async (chat: Chat) => { if (await open(chat.id, chat.focus)) onClose() }
  return (
    <div className="conversation-search chats-panel" role="region" aria-label="Chats" onKeyDown={(event) => { if (event.key === 'Escape') onClose() }}>
      <div className="search-bar chats-bar">
        <h2>Chats</h2>
        <button type="button" className="icon-button" aria-label="Close chats" onClick={onClose}><X aria-hidden="true" /></button>
      </div>
      <div className="search-results">
        {chats.isPending && <Loading label="Loading your chats" />}
        {chats.isError && <ErrorNotice error={chats.error} />}
        {error && <Notice tone="error">{error}</Notice>}
        <ul className="chat-list">
          {(chats.data?.chats ?? []).map((chat) => (
            <li key={`${chat.kind}:${chat.id}`}>
              <button type="button" className={`chat-row${chat.focus ? ' current' : ''}${chat.unread ? ' unread' : ''}`} aria-label={chatLabel(chat)}
                aria-current={chat.focus ? 'true' : undefined} disabled={busy !== null} onClick={() => void choose(chat)}>
                <ChatAvatar chat={chat} />
                <span className="chat-row-text">
                  <span className="chat-row-top"><strong>{chat.name}</strong>{chat.last && <Stamp className="chat-row-time" value={chat.last.at} />}</span>
                  <span className="chat-row-preview">{busy === chat.id ? 'Opening…' : preview(chat)}</span>
                </span>
                {chat.unread > 0 && <span className="unread-badge" aria-hidden="true">{badge(chat.unread)}</span>}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export function ChatAvatar({ chat }: { chat: Chat }) {
  const portrait = usePortrait()
  // Only the companion in focus has their picture loaded; the others show their initial.
  if (chat.focus && portrait) return <img className="portrait" src={portrait} alt="" aria-hidden="true" />
  return <span className="portrait" aria-hidden="true">{chat.name.slice(0, 1).toUpperCase()}</span>
}
