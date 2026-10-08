import type { View } from '../../companion'
import type { Chat, ChatStyle } from '../../types'
import { Stamp } from '../../components/Stamp'
import { badge, chatLabel, preview } from './chatText'
import { ChatAvatar } from './ChatsPanel'
import { useChats, useOpenChat } from './useChats'

/**
 * The chat list beside the chat on a wide screen, in the look of the app each style borrows from: a rail of
 * round pictures for Community, a buddy list window for Retro IM, a conversation list for the others. Only
 * names, the latest message, when, and what is unread: never whether anyone is online, away or typing.
 * Phones use the Chats button instead (ChatsPanel).
 */
export function ChatSidebar({ style, retroDark, go }: { style: ChatStyle; retroDark: boolean; go: (view: View) => void }) {
  const chats = useChats().data?.chats ?? []
  const { open, busy } = useOpenChat(go)
  if (chats.length < 2) return null
  const choose = (chat: Chat) => void open(chat.id, chat.focus)
  if (style === 'community') return <Rail chats={chats} busy={busy} onOpen={choose} />
  if (style === 'retro') return <BuddyList chats={chats} busy={busy} dark={retroDark} onOpen={choose} />
  return (
    <nav className={`chat-side side-list side-${style}`} aria-label="Chats">
      <h2 className="side-title">Chats</h2>
      <ul>
        {chats.map((chat) => (
          <li key={`${chat.kind}:${chat.id}`}>
            <button type="button" className={`chat-row${chat.focus ? ' current' : ''}${chat.unread ? ' unread' : ''}`} aria-label={chatLabel(chat)}
              aria-current={chat.focus ? 'true' : undefined} disabled={busy !== null} onClick={() => choose(chat)}>
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
    </nav>
  )
}

type ListProps = { chats: Chat[]; busy: string | null; onOpen: (chat: Chat) => void }

/** Community: round pictures down the side, a pill beside the open one and a count on the ones with news. */
function Rail({ chats, busy, onOpen }: ListProps) {
  return (
    <nav className="chat-side side-rail" aria-label="Chats">
      <ul>
        {chats.map((chat) => (
          <li key={`${chat.kind}:${chat.id}`} className={`${chat.focus ? 'current' : ''}${chat.unread ? ' unread' : ''}`}>
            <button type="button" className="rail-button" title={chat.name} aria-label={chatLabel(chat)} aria-current={chat.focus ? 'true' : undefined}
              disabled={busy !== null} onClick={() => onOpen(chat)}>
              <ChatAvatar chat={chat} />
              {chat.unread > 0 && <span className="unread-badge" aria-hidden="true">{badge(chat.unread)}</span>}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  )
}

/** Retro IM: a buddy list window. One group of everyone, names in bold with a count when something is new. */
function BuddyList({ chats, busy, dark, onOpen }: ListProps & { dark: boolean }) {
  return (
    <nav className={`chat-retro${dark ? ' retro-dark' : ''} chat-side side-buddies`} aria-label="Chats">
      <div className="buddy-titlebar" aria-hidden="true">Buddy List</div>
      <h2 className="buddy-group">Buddies ({chats.length})</h2>
      <ul>
        {chats.map((chat) => (
          <li key={`${chat.kind}:${chat.id}`}>
            <button type="button" className={`buddy${chat.focus ? ' current' : ''}${chat.unread ? ' unread' : ''}`} aria-label={chatLabel(chat)}
              aria-current={chat.focus ? 'true' : undefined} disabled={busy !== null} onClick={() => onOpen(chat)}>
              <span className="buddy-name">{chat.name}</span>
              {chat.unread > 0 && <span className="buddy-count" aria-hidden="true">({badge(chat.unread)})</span>}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  )
}
