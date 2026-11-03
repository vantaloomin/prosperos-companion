import { useEffect } from 'react'
import { PanelLeft, PanelRight, PanelTop } from 'lucide-react'
import { useChatStyle } from '../conversation/useChatStyle'
import { useChats } from './useChats'
import { useChatListCollapsed } from './layout'
import { listButtonLabel, othersUnread, type OpenChat } from './chatText'

/**
 * The panel button at the top left of a chat on a wide screen: it hides or shows the chat list beside the chat,
 * and so does the [ key. Hidden, the chat sits in the middle of the window (testers: a centered chat matters for
 * health and ergonomics), and a dot shows that something new waits in the list. Remembered on this device.
 * Phones have the list as their own screen, so they use Back instead.
 */
export function ListButton({ current = null }: { current?: OpenChat }) {
  const [collapsed, setCollapsed] = useChatListCollapsed()
  const chats = useChats().data?.chats ?? []
  useListKey(collapsed, setCollapsed)
  // The icon points to where the list is: Retro IM's buddy list sits right, Feed's tray across the top.
  const style = useChatStyle().style
  const Icon = style === 'retro' ? PanelRight : style === 'feed' ? PanelTop : PanelLeft
  if (!chats.length) return null
  const waiting = collapsed ? othersUnread(chats, current) : 0
  const label = listButtonLabel(!collapsed, waiting)
  return (
    <button type="button" className="icon-button list-button desktop-only" aria-label={label} title={`${label}  [`} aria-pressed={!collapsed} onClick={() => setCollapsed(!collapsed)}>
      <Icon aria-hidden="true" />{waiting > 0 && <span className="nav-dot" aria-hidden="true" />}
    </button>
  )
}

/** [ toggles the list, except while typing or with a modifier held. */
function useListKey(collapsed: boolean, setCollapsed: (collapsed: boolean) => void) {
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      if (event.key !== '[' || event.ctrlKey || event.metaKey || event.altKey || typing(event.target)) return
      event.preventDefault()
      setCollapsed(!collapsed)
    }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [collapsed, setCollapsed])
}

function typing(target: EventTarget | null): boolean {
  const element = target as HTMLElement | null
  return !!element && (element.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(element.tagName))
}
