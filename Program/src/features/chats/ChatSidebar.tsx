import type { View } from '../../companion'
import type { Chat, ChatStyle } from '../../types'
import { Stamp } from '../../components/Stamp'
import { badge, chatLabel, isOpen, preview, type OpenChat } from './chatText'
import { ChatAvatar } from './ChatsPanel'
import { useChats, useOpenChat } from './useChats'
import { useChatListCollapsed, useChatListWidth } from './layout'
import { CollapseButton, ResizeHandle } from './SideControls'
import { StatusText } from '../status/StatusLine'

/**
 * The chat list beside the chat on a wide screen, in the look of the app each style borrows from: a rail of
 * round pictures for Community, a buddy list window for Retro IM, a tray of ringed pictures across the top for
 * Feed, a cast of portrait cards for Visual novel and a conversation list for Bubbles. Only
 * names, the latest message, when, what is unread and, in the buddy list, their status or away message
 * (companion/life/status.py): never an online or idle dot, and never whether anyone is typing.
 * Phones use the Chats button instead (ChatsPanel). It can be hidden, and the side lists made wider or narrower,
 * on this device (layout.ts).
 */
export function ChatSidebar({ style, retroDark, go, current = null }: { style: ChatStyle; retroDark: boolean; go: (view: View) => void; current?: OpenChat }) {
  const chats = useChats().data?.chats ?? []
  const { open, busy } = useOpenChat(go)
  const [collapsed] = useChatListCollapsed()
  if (chats.length < 2 || collapsed) return null
  const here = (chat: Chat) => isOpen(chat, current)
  const choose = (chat: Chat) => void open(chat, here(chat))
  const props = { chats, busy, here, current, onOpen: choose }
  if (style === 'community') return <Rail {...props} />
  if (style === 'retro') return <BuddyList {...props} dark={retroDark} />
  if (style === 'feed') return <Tray {...props} />
  if (style === 'novel') return <Cast {...props} />
  return <ConversationList {...props} style={style} />
}

type ListProps = { chats: Chat[]; busy: string | null; here: (chat: Chat) => boolean; current: OpenChat; onOpen: (chat: Chat) => void }

/** Bubbles: a conversation list, as in a desktop messaging app. */
function ConversationList({ chats, busy, here, current, style, onOpen }: ListProps & { style: ChatStyle }) {
  const [width, setWidth] = useChatListWidth('list')
  const choose = onOpen
  return (
    <nav className={`chat-side side-list side-${style}`} aria-label="Chats" style={{ width }}>
      <div className="side-head"><h2 className="side-title">Chats</h2><CollapseButton /></div>
      <ul>
        {chats.map((chat) => (
          <li key={`${chat.kind}:${chat.id}`}>
            <button type="button" className={`chat-row${here(chat) ? ' current' : ''}${chat.unread ? ' unread' : ''}`} aria-label={chatLabel(chat, current)}
              aria-current={here(chat) ? 'true' : undefined} disabled={busy !== null} onClick={() => choose(chat)}>
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
      <ResizeHandle kind="list" width={width} onWidth={setWidth} />
    </nav>
  )
}

/** Community: round pictures down the side, a pill beside the open one and a count on the ones with news. */
function Rail({ chats, busy, here, current, onOpen }: ListProps) {
  return (
    <nav className="chat-side side-rail" aria-label="Chats">
      <ul>
        {chats.map((chat) => (
          <li key={`${chat.kind}:${chat.id}`} className={`${here(chat) ? 'current' : ''}${chat.unread ? ' unread' : ''}`}>
            <button type="button" className="rail-button" title={chat.name} aria-label={chatLabel(chat, current)} aria-current={here(chat) ? 'true' : undefined}
              disabled={busy !== null} onClick={() => onOpen(chat)}>
              <ChatAvatar chat={chat} />
              {chat.unread > 0 && <span className="unread-badge" aria-hidden="true">{badge(chat.unread)}</span>}
            </button>
          </li>
        ))}
      </ul>
      <CollapseButton />
    </nav>
  )
}

/** Retro IM: a buddy list window. One group of everyone, names in bold with a count when something is new. */
function BuddyList({ chats, busy, here, current, dark, onOpen }: ListProps & { dark: boolean }) {
  const [width, setWidth] = useChatListWidth('buddies')
  return (
    <nav className={`chat-retro${dark ? ' retro-dark' : ''} chat-side side-buddies`} aria-label="Chats" style={{ width }}>
      <div className="buddy-titlebar"><span aria-hidden="true">Buddy List</span><CollapseButton side="right" /></div>
      <ResizeHandle kind="buddies" width={width} onWidth={setWidth} side="right" />
      <h2 className="buddy-group">Buddies ({chats.length})</h2>
      <ul>
        {chats.map((chat) => (
          <li key={`${chat.kind}:${chat.id}`}>
            <button type="button" className={`buddy${here(chat) ? ' current' : ''}${chat.unread ? ' unread' : ''}`} aria-label={chatLabel(chat, current)}
              aria-current={here(chat) ? 'true' : undefined} disabled={busy !== null} onClick={() => onOpen(chat)}>
              <span className="buddy-text">
                <span className="buddy-top"><span className="buddy-name">{chat.name}</span>
                  {chat.unread > 0 && <span className="buddy-count" aria-hidden="true">({badge(chat.unread)})</span>}</span>
                <StatusText name={chat.name} status={chat.status} className="buddy-status" />
              </span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  )
}

/** Feed: a tray of pictures across the top, the way a social app shows who has something new: a ring for news. */
function Tray({ chats, busy, here, current, onOpen }: ListProps) {
  return (
    <nav className="chat-side side-tray" aria-label="Chats">
      <ul>
        {chats.map((chat) => (
          <li key={`${chat.kind}:${chat.id}`}>
            <button type="button" className={`tray-item${here(chat) ? ' current' : ''}${chat.unread ? ' unread' : ''}`} aria-label={chatLabel(chat, current)}
              aria-current={here(chat) ? 'true' : undefined} disabled={busy !== null} onClick={() => onOpen(chat)}>
              <span className="tray-ring"><ChatAvatar chat={chat} /></span>
              {chat.unread > 0 && <span className="unread-badge" aria-hidden="true">{badge(chat.unread)}</span>}
              <span className="tray-name">{chat.name}</span>
            </button>
          </li>
        ))}
      </ul>
      <CollapseButton />
    </nav>
  )
}

/** Visual novel: the cast as portrait cards, like choosing whose route to follow, with a ribbon for news. */
function Cast({ chats, busy, here, current, onOpen }: ListProps) {
  const [width, setWidth] = useChatListWidth('cast')
  return (
    <nav className="chat-side side-cast" aria-label="Chats" style={{ width }}>
      <div className="side-head"><h2 className="side-title">Cast</h2><CollapseButton /></div>
      <ul>
        {chats.map((chat) => (
          <li key={`${chat.kind}:${chat.id}`}>
            <button type="button" className={`cast-card${here(chat) ? ' current' : ''}${chat.unread ? ' unread' : ''}`} aria-label={chatLabel(chat, current)}
              aria-current={here(chat) ? 'true' : undefined} disabled={busy !== null} onClick={() => onOpen(chat)}>
              <span className="cast-arch"><ChatAvatar chat={chat} /></span>
              <span className="cast-name">{chat.name}</span>
              {chat.last && <span className="cast-line">{busy === chat.id ? 'Opening…' : preview(chat)}</span>}
              {chat.unread > 0 && <span className="cast-ribbon" aria-hidden="true">{badge(chat.unread)} new</span>}
            </button>
          </li>
        ))}
      </ul>
      <ResizeHandle kind="cast" width={width} onWidth={setWidth} />
    </nav>
  )
}
