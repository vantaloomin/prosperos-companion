import { PanelLeftOpen, UsersRound, X } from 'lucide-react'
import type { View } from '../../companion'
import type { Chat } from '../../types'
import { Stamp } from '../../components/Stamp'
import { Loading, Notice } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { usePortrait } from '../conversation/portrait'
import { badge, chatLabel, isOpen, preview, type OpenChat } from './chatText'
import { useChats, useOpenChat } from './useChats'
import { useChatListCollapsed } from './layout'

/**
 * Every chat, the most recent first, the way a messaging app lists them: who, their latest message, when, and
 * how many are unread. Never whether anyone is around. On a phone it covers the screen.
 */
export function ChatsPanel({ go, onClose, current = null }: { go: (view: View) => void; onClose: () => void; current?: OpenChat }) {
  const [collapsed, setCollapsed] = useChatListCollapsed()
  return (
    <div className="conversation-search chats-panel" role="region" aria-label="Chats" onKeyDown={(event) => { if (event.key === 'Escape') onClose() }}>
      <div className="search-bar chats-bar">
        <h2>Chats</h2>
        {/* On a wide screen the list can stay beside the chat again; phones always use this one. */}
        {collapsed && <button type="button" className="text-button side-expand" onClick={() => { setCollapsed(false); onClose() }}><PanelLeftOpen aria-hidden="true" />Keep beside the chat</button>}
        <button type="button" className="icon-button" aria-label="Close chats" onClick={onClose}><X aria-hidden="true" /></button>
      </div>
      <ChatList go={go} current={current} onOpened={onClose} />
    </div>
  )
}

/** The rows themselves, shared by this panel and the phone's Chats tab (ChatsHome). */
export function ChatList({ go, current = null, onOpened }: { go: (view: View) => void; current?: OpenChat; onOpened?: () => void }) {
  const chats = useChats()
  const { open, busy, error } = useOpenChat(go)
  const choose = async (chat: Chat) => { if (await open(chat, isOpen(chat, current))) onOpened?.() }
  return (
    <div className="search-results">
      {chats.isPending && <Loading label="Loading your chats" />}
      {chats.isError && <ErrorNotice error={chats.error} />}
      {error && <Notice tone="error">{error}</Notice>}
      <ul className="chat-list">
        {(chats.data?.chats ?? []).map((chat) => (
          <li key={`${chat.kind}:${chat.id}`}>
            <button type="button" className={`chat-row${isOpen(chat, current) ? ' current' : ''}${chat.unread ? ' unread' : ''}`} aria-label={chatLabel(chat, current)}
              aria-current={isOpen(chat, current) ? 'true' : undefined} disabled={busy !== null} onClick={() => void choose(chat)}>
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
  )
}

export function ChatAvatar({ chat }: { chat: Chat }) {
  const portrait = usePortrait()
  if (chat.kind === 'group') return <span className="portrait" aria-hidden="true"><UsersRound /></span>
  // Only the companion in focus has their picture loaded; the others show their initial.
  if (chat.focus && portrait) return <img className="portrait" src={portrait} alt="" aria-hidden="true" />
  return <span className="portrait" aria-hidden="true">{chat.name.slice(0, 1).toUpperCase()}</span>
}
