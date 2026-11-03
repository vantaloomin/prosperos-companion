import { Fragment, useEffect, useRef } from 'react'
import { BookOpen, CalendarDays, Download, Eye, Heart, MessageCircle, Settings as SettingsIcon, UserPlus, UserRound } from 'lucide-react'
import type { View } from '../../companion'
import { badge } from '../chats/chatText'
import { WorldButton } from '../worlds/WorldButton'
import { chatsTarget, inChats, railCurrent } from './navText'
import { useEraWords } from '../world/useEraWords'
import { isActive, navLabel, percent, type ReadyView } from '../ready/readyText'
import { useReady, useReadyActions } from '../ready/useReady'

/**
 * The views. The desktop side rail shows all of them; the phone's tab bar (`rail-only` hidden) keeps Today, Story,
 * Matchlight and Settings, with its own Chats tab (navText.ts). Group chats are in the Chats list on both. The rail's
 * Chats opens the companion's chat; their profile (Posts, Memories, Character) opens from their name and keeps Chats
 * lit, so Memories left the rail in 1.3. While the user is just
 * watching, Watching takes Matchlight's place (Matchlight waits meanwhile), so the phone still has five tabs.
 */
type NavView = { id: View; label: string; icon: typeof UserRound; railOnly?: boolean }
const WATCHING: NavView = { id: 'watch', label: 'Watching', icon: Eye }
const VIEWS: NavView[] = [
  { id: 'conversation', label: 'Chats', icon: MessageCircle, railOnly: true },
  { id: 'dating', label: 'Matchlight', icon: Heart },
  { id: 'story', label: 'Story', icon: BookOpen },
  { id: 'today', label: 'Today', icon: CalendarDays },
  { id: 'settings', label: 'Settings', icon: SettingsIcon },
]

interface Props {
  view: View
  go: (view: View) => void
  storyOn: boolean
  datingInstalled: boolean
  /** Matchlight is a phone app to install there (not a website, the paper or the matchmaker). */
  datingApp?: boolean
  unread: { companion: number; group: number }
  watching?: boolean
}

export function AppNav({ view, go, storyOn, datingInstalled, datingApp = true, unread, watching }: Props) {
  // Group chats share the Chats list now, so the rail's Chats counts both, as the phone's tab does.
  const counts: Partial<Record<string, number>> = { conversation: unread.companion + unread.group }
  const ready = useSettingsMark(view)
  // Matchlight goes by the era's name: the Personals in 1895, the Matchmaker in Camelot (eraWords.ts).
  const dating = useEraWords().dating_tab
  return (
    <nav className="app-nav" aria-label="Views">
      <WorldButton current={view === 'worlds'} onOpen={() => go('worlds')} />
      <ChatsTab view={view} go={go} unread={unread.companion + unread.group} />
      {VIEWS.map((item) => watching && item.id === 'dating' ? WATCHING : item).filter(({ id }) => id !== 'story' || storyOn).map(({ id, label, icon: Icon, railOnly }) => (
        <Fragment key={id}>
          <button type="button" className={`nav-${id}${railOnly ? ' rail-only' : ''}`} aria-current={railCurrent(id, view) ? 'page' : undefined} onClick={() => go(id)}
            aria-label={id === 'settings' ? navLabel(ready) : undefined}>
            <Icon aria-hidden="true" />{id === 'dating' && !datingInstalled && <DatingBadge app={datingApp} />}
            {id === 'settings' && <SettingsMark view={ready} />}
            <Count count={counts[id]} /><span>{id === 'dating' ? dating : label}</span>
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

/** "Set it up for me" as the Settings tab shows it; opening Settings once clears the done dot. */
function useSettingsMark(view: View): ReadyView | undefined {
  const ready = useReady().data
  const { seen } = useReadyActions()
  const unseen = ready?.status === 'ready' && !ready.settings_seen
  useEffect(() => { if (unseen && view.startsWith('settings')) void seen('settings') }, [unseen, view, seen])
  return ready
}

/** A thin ring in the badge spot while the model downloads (static, so Less motion changes nothing), then a dot. */
function SettingsMark({ view }: { view?: ReadyView }) {
  if (view && isActive(view) && view.status !== 'cancelled') {
    const length = 2 * Math.PI * 7
    return <svg className="nav-ring" viewBox="0 0 18 18" aria-hidden="true">
      <circle cx="9" cy="9" r="7" className="nav-ring-track" />
      <circle cx="9" cy="9" r="7" className="nav-ring-fill" strokeDasharray={`${length * percent(view) / 100} ${length}`} />
    </svg>
  }
  return view?.status === 'ready' && !view.settings_seen ? <span className="nav-dot" aria-hidden="true" /> : null
}

/** Matchlight not set up yet: a download where it is a phone app, signing up anywhere else (Iris, 2026-10-29). */
function DatingBadge({ app }: { app: boolean }) {
  return app ? <Download className="nav-badge" aria-label="not installed" /> : <UserPlus className="nav-badge" aria-label="not signed up" />
}
