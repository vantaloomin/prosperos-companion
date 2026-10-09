import { Fragment, lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react'
import { BookHeart, BookOpen, CalendarDays, Download, Heart, MessageSquareText, Settings as SettingsIcon, UserRound, UsersRound } from 'lucide-react'
import type { Companion } from './types'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './api'
import { useCompanion, useFollowPcTimezone, useWorkspaceSettings, type View } from './companion'
import { Conversation } from './features/conversation/Conversation'
import type { SettingsTab } from './features/settings/sections'
import { useReconcile } from './features/today/useReconcile'
import { useNotifications } from './features/notifications/useNotifications'
import { useTexts } from './features/conversation/useTexts'
import { Loading, Notice } from './components/Feedback'
import { ErrorNotice } from './components/ErrorNotice'
import { DebugBanner } from './features/settings/DebugBanner'
import { Profile } from './features/profile/Profile'
import { profileTab } from './features/profile/profileText'
import { Welcome } from './features/character/Welcome'
import { AiNotice } from './features/character/AiNotice'
import { sidecar, useSidecarOpen } from './features/sidecar/store'
import { useChats } from './features/chats/useChats'
import { reach } from './features/notifications/useNotifications'
import { badge, unreadOf } from './features/chats/chatText'
import { WorldButton } from './features/worlds/WorldButton'
import { useAppColors } from './features/settings/useAppColors'

// Chat opens first, so it ships in the main bundle; every other view loads the first time it is opened.
const Character = lazy(() => import('./features/character/Character').then((m) => ({ default: m.Character })))
const SwitchTo = lazy(() => import('./features/character/SwitchTo').then((m) => ({ default: m.SwitchTo })))
const Appearance = lazy(() => import('./features/appearance/Appearance').then((m) => ({ default: m.Appearance })))
const Portraits = lazy(() => import('./features/appearance/Portraits').then((m) => ({ default: m.Portraits })))
const Memories = lazy(() => import('./features/memories/Memories').then((m) => ({ default: m.Memories })))
const Settings = lazy(() => import('./features/settings/Settings').then((m) => ({ default: m.Settings })))
const Today = lazy(() => import('./features/today/Today').then((m) => ({ default: m.Today })))
const Dating = lazy(() => import('./features/dating/Dating').then((m) => ({ default: m.Dating })))
const Story = lazy(() => import('./features/story/Story').then((m) => ({ default: m.Story })))
const Sidecar = lazy(() => import('./features/sidecar/Sidecar').then((m) => ({ default: m.Sidecar })))
const Groups = lazy(() => import('./features/groups/Groups').then((m) => ({ default: m.Groups })))
const GroupChat = lazy(() => import('./features/groups/GroupChat').then((m) => ({ default: m.GroupChat })))
const Worlds = lazy(() => import('./features/worlds/Worlds').then((m) => ({ default: m.Worlds })))
const Feed = lazy(() => import('./features/feed/Feed').then((m) => ({ default: m.Feed })))

// The companion's profile holds the chat (Messages), the feed (Posts) and the character as tabs.
const VIEWS: { id: View; label: string; icon: typeof UserRound }[] = [
  { id: 'conversation', label: 'Profile', icon: UserRound },
  { id: 'groups', label: 'Groups', icon: UsersRound },
  { id: 'dating', label: 'Matchlight', icon: Heart },
  { id: 'story', label: 'Story', icon: BookOpen },
  { id: 'today', label: 'Today', icon: CalendarDays },
  { id: 'memories', label: 'Memories', icon: BookHeart },
  { id: 'settings', label: 'Settings', icon: SettingsIcon },
]

function viewFromHash(): View {
  const id = window.location.hash.slice(1)
  return id === 'worlds' || VIEWS.some((view) => view.id === id) || profileTab(id) || id.startsWith('settings/') || id.startsWith('match/') || id.startsWith('chat/') || id.startsWith('group/') ? id as View : 'conversation'
}

function isCurrent(id: View, view: View) {
  return view === id || (id === 'conversation' && profileTab(view) !== null) || (id === 'settings' && view.startsWith('settings/')) || (id === 'groups' && view.startsWith('group/'))
}

export default function App() {
  const [view, setView] = useState<View>(viewFromHash)
  const companion = useCompanion()
  useReconcile(!!companion.data)
  useFollowPcTimezone()
  useEffect(() => {
    const sync = () => setView(viewFromHash())
    window.addEventListener('popstate', sync)
    return () => window.removeEventListener('popstate', sync)
  }, [])
  const go = useCallback((next: View) => { window.history.pushState(null, '', `#${next}`); setView(next) }, [])
  // Switching Settings tabs keeps the address deep-linkable without filling the back button with tabs.
  const openTab = useCallback((tab: SettingsTab) => { window.history.replaceState(null, '', `#settings/${tab}`); setView(`settings/${tab}`) }, [])
  useNotifications(!!companion.data, go)
  useTexts(!!companion.data)
  useChatLink(view, setView)
  const chats = useChats(!!companion.data).data?.chats ?? []
  // Unread one-to-one chats count on Profile, group chats on Groups.
  const unread: Partial<Record<string, number>> = { conversation: unreadOf(chats, 'companion'), groups: unreadOf(chats, 'group') }
  useFocusOnViewChange(view)
  // Story mode is opt-in (Settings > Advanced), so its tab shows only once it is on.
  const storyOn = !!useWorkspaceSettings().data?.story_mode
  useAppColors()
  const sidecarOpen = useSidecarOpen()
  // The dating app shows a download badge until the user has set it up (src/features/dating).
  const datingInstalled = useQuery({ queryKey: ['dating-status'], queryFn: () => api<{ installed: boolean }>('/dating/status') }).data?.installed ?? true
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">Skip to content</a>
      <nav className="app-nav" aria-label="Views">
        <WorldButton current={view === 'worlds'} onOpen={() => go('worlds')} />
        {VIEWS.filter(({ id }) => id !== 'story' || storyOn).map(({ id, label, icon: Icon }) => (
          <Fragment key={id}>
            {/* The sidecar opens beside any view, so it is a toggle rather than a view. */}
            {id === 'settings' && <button type="button" className="nav-sidecar" aria-pressed={sidecarOpen} onClick={() => sidecar.setOpen(!sidecarOpen)}>
              <MessageSquareText aria-hidden="true" /><span>Sidecar</span>
            </button>}
            <button type="button" aria-current={isCurrent(id, view) ? 'page' : undefined} onClick={() => go(id)}>
              <Icon aria-hidden="true" />{id === 'dating' && !datingInstalled && <Download className="nav-badge" aria-label="not installed" />}
              {!!unread[id] && <span className="nav-count" aria-label={`${unread[id]} unread`}>{badge(unread[id])}</span>}<span>{label}</span>
            </button>
          </Fragment>
        ))}
      </nav>
      <main id="main" className="app-main" tabIndex={-1}>
        <DebugBanner onOpen={() => go('settings/debug')} />
        {companion.isPending ? <Loading label="Opening your companion" />
          : companion.isError ? <ErrorNotice error={companion.error} />
            : <Suspense fallback={<Loading label="Opening" />}><CurrentView view={view} companion={companion.data ?? null} go={go} openTab={openTab} /></Suspense>}
      </main>
      {sidecarOpen && <Suspense fallback={null}><Sidecar view={view} go={go} /></Suspense>}
      <AiNotice />
    </div>
  )
}

/** #chat/<id>, from a notification tapped while the app was closed: open that companion's chat. */
function useChatLink(view: View, setView: (view: View) => void) {
  const client = useQueryClient()
  useEffect(() => {
    if (!view.startsWith('chat/')) return
    // The chat takes this address's place, so Back does not open it again.
    const open = (next: View) => { window.history.replaceState(null, '', `#${next}`); setView(next) }
    void reach(client, open, 'conversation', decodeURIComponent(view.slice(5)))
  }, [view, client, setView])
}

/**
 * A button inside a view that opens another view is gone once it renders, which leaves focus on the
 * page body. Start the new view from its top instead; focus on a nav button or set by the view stays.
 */
function useFocusOnViewChange(view: View) {
  const first = useRef(true)
  useEffect(() => {
    if (first.current) { first.current = false; return }
    if (document.activeElement === document.body) document.getElementById('main')?.focus({ preventScroll: true })
  }, [view])
}

interface CurrentViewProps { view: View; companion: Companion | null; go: (view: View) => void; openTab: (tab: SettingsTab) => void }

function CurrentView({ view, companion, go, openTab }: CurrentViewProps) {
  const loraMaker = useWorkspaceSettings().data?.lora_maker
  // Settings, the dating app, the story and group chats belong to the workspace, so they open with or without a companion.
  if (inWorkspace(view)) return <WorkspaceView view={view} companion={companion} go={go} openTab={openTab} />
  // With the LoRA creator switched off (the default), an old #appearance link opens the Character page.
  const shown = view === 'appearance' && !loraMaker ? 'character' : view
  if (!companion) return shown === 'character' ? <Character companion={null} go={go} /> : <Welcome go={go} />
  const page = shown === 'character' ? <Character companion={companion} go={go} /> : <CompanionView view={shown} companion={companion} go={go} />
  return profileTab(shown) ? <Profile companion={companion} view={shown} go={go}>{page}</Profile> : page
}

function inWorkspace(view: View) {
  return view === 'worlds' || view === 'settings' || view.startsWith('settings/') || view === 'story' || view === 'dating' || view.startsWith('match/')
    || view === 'groups' || view.startsWith('group/')
}

function WorkspaceView({ view, companion, go, openTab }: CurrentViewProps) {
  const storyOn = useWorkspaceSettings().data?.story_mode
  if (view === 'worlds') return <Worlds />
  if (view === 'dating') return <Dating go={go} />
  if (view === 'groups') return <Groups go={go} />
  if (view.startsWith('group/')) return <GroupChat key={view} id={decodeURIComponent(view.slice(6))} go={go} />
  if (view.startsWith('match/')) return <SwitchTo townKey={decodeURIComponent(view.slice(6))} go={go} />
  if (view !== 'story') return <Settings companion={companion} tab={view.split('/')[1]} onTab={openTab} onCreate={() => go('character')} />
  return storyOn ? <Story go={go} />
    : <Notice action={<button type="button" className="text-button" onClick={() => go('settings/advanced')}>Open Settings</button>}>Story mode is off. Turn it on in Settings &gt; Advanced.</Notice>
}

function CompanionView({ view, companion, go }: { view: View; companion: Companion; go: (view: View) => void }) {
  if (view.startsWith('cast/')) return <SwitchTo townKey={decodeURIComponent(view.slice(5))} go={go} />
  if (view === 'appearance') return <Appearance companion={companion} go={go} />
  if (view === 'portraits') return <Portraits companion={companion} go={go} />
  if (view === 'today') return <Today companion={companion} go={go} />
  if (view === 'feed') return <Feed companion={companion} go={go} />
  if (view === 'memories') return <Memories companion={companion} />
  return <Conversation companion={companion} go={go} />
}
