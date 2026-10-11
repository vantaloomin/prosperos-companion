import { Fragment, useEffect, useRef } from 'react'
import { BookHeart, BookOpen, CalendarDays, Download, Heart, MessageCircle, MessageSquareText, Settings as SettingsIcon, UserRound, UsersRound } from 'lucide-react'
import type { View } from '../../companion'
import { badge } from '../chats/chatText'
import { WorldButton } from '../worlds/WorldButton'
import { toggleSidecar } from '../sidecar/toggle'
import { chatsTarget, inChats, railCurrent } from './navText'

/**
 * The views. The desktop side rail shows all of them; the phone's tab bar (`rail-only` hidden) keeps Today, Story,
 * Matchlight and Settings, with Chats in place of Profile, Groups and Memories (navText.ts).
 */
const VIEWS: { id: View; label: string; icon: typeof UserRound; railOnly?: boolean }[] = [
  { id: 'conversation', label: 'Profile', icon: UserRound, railOnly: true },
  { id: 'groups', label: 'Groups', icon: UsersRound, railOnly: true },
  { id: 'dating', label: 'Matchlight', icon: Heart },
  { id: 'story', label: 'Story', icon: BookOpen },
  { id: 'today', label: 'Today', icon: CalendarDays },
  { id: 'memories', label: 'Memories', icon: BookHeart, railOnly: true },
  { id: 'settings', label: 'Settings', icon: SettingsIcon },
]

interface Props {
  view: View
  go: (view: View) => void
  storyOn: boolean
  datingInstalled: boolean
  unread: { companion: number; group: number }
  sidecarOpen: boolean
  sidecarWaiting: boolean
}

export function AppNav({ view, go, storyOn, datingInstalled, unread, sidecarOpen, sidecarWaiting }: Props) {
  const counts: Partial<Record<string, number>> = { conversation: unread.companion, groups: unread.group }
  return (
    <nav className="app-nav" aria-label="Views">
      <WorldButton current={view === 'worlds'} onOpen={() => go('worlds')} />
      <ChatsTab view={view} go={go} unread={unread.companion + unread.group} />
      {VIEWS.filter(({ id }) => id !== 'story' || storyOn).map(({ id, label, icon: Icon, railOnly }) => (
        <Fragment key={id}>
          {/* The sidecar opens beside any view, so it is a toggle rather than a view. On a phone it is in the chat header. */}
          {id === 'settings' && <button type="button" className="nav-sidecar rail-only" aria-pressed={sidecarOpen} onClick={() => toggleSidecar(sidecarOpen)}>
            <MessageSquareText aria-hidden="true" />{sidecarWaiting && <span className="nav-dot" aria-label="something waiting" />}<span>Sidecar</span>
          </button>}
          <button type="button" className={`nav-${id}${railOnly ? ' rail-only' : ''}`} aria-current={railCurrent(id, view) ? 'page' : undefined} onClick={() => go(id)}>
            <Icon aria-hidden="true" />{id === 'dating' && !datingInstalled && <Download className="nav-badge" aria-label="not installed" />}
            <Count count={counts[id]} /><span>{label}</span>
          </button>
        </Fragment>
      ))}
    </nav>
  )
}

/** The phone's first tab. It goes back to where the user was under Chats, or to the list when tapped there. */
function ChatsTab({ view, go, unread }: { view: View; go: (view: View) => void; unread: number }) {
  const last = useRef<View>('conversation')
  useEffect(() => { if (inChats(view)) last.current = view }, [view])
  const here = inChats(view)
  return (
    <button type="button" className="nav-chats phone-only" aria-current={here ? 'page' : undefined} onClick={() => { if (view !== 'chats') go(chatsTarget(view, last.current) as View) }}>
      <MessageCircle aria-hidden="true" /><Count count={unread} /><span>Chats</span>
    </button>
  )
}

function Count({ count }: { count?: number }) {
  return count ? <span className="nav-count" aria-label={`${count} unread`}>{badge(count)}</span> : null
}
