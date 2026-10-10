import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react'
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
import { useSidecarMode, useSidecarOpen, useSidecarWaiting } from './features/sidecar/store'
import { useChats } from './features/chats/useChats'
import { reach } from './features/notifications/useNotifications'
import { unreadOf } from './features/chats/chatText'
import { AppNav } from './features/nav/AppNav'
import { RAIL_IDS, fromToday } from './features/nav/navText'
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
const SidecarWindow = lazy(() => import('./features/sidecar/SidecarWindow').then((m) => ({ default: m.SidecarWindow })))
const Groups = lazy(() => import('./features/groups/Groups').then((m) => ({ default: m.Groups })))
const GroupChat = lazy(() => import('./features/groups/GroupChat').then((m) => ({ default: m.GroupChat })))
const Worlds = lazy(() => import('./features/worlds/Worlds').then((m) => ({ default: m.Worlds })))
const WhoKnowsWho = lazy(() => import('./features/web/WhoKnowsWho').then((m) => ({ default: m.WhoKnowsWho })))
const CityMap = lazy(() => import('./features/map/CityMap').then((m) => ({ default: m.CityMap })))
const Feed = lazy(() => import('./features/feed/Feed').then((m) => ({ default: m.Feed })))
const ChatsHome = lazy(() => import('./features/chats/ChatsHome').then((m) => ({ default: m.ChatsHome })))

// Views outside the side rail: the phone's Chats list, worlds, and the map and Who knows who opened from Today.
const OTHER_VIEWS = new Set(['chats', 'worlds', 'people', 'map'])
const LINKED = ['settings/', 'match/', 'chat/', 'group/', 'map/']

function viewFromHash(): View {
  const id = window.location.hash.slice(1)
  return OTHER_VIEWS.has(id) || RAIL_IDS.has(id) || profileTab(id) || LINKED.some((prefix) => id.startsWith(prefix)) ? id as View : 'conversation'
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
  // Unread one-to-one chats count on Profile, group chats on Groups, and both on the phone's Chats.
  const unread = { companion: unreadOf(chats, 'companion'), group: unreadOf(chats, 'group') }
  useFocusOnViewChange(view)
  // Story mode is opt-in (Settings > Advanced), so its tab shows only once it is on.
  const storyOn = !!useWorkspaceSettings().data?.story_mode
  useAppColors()
  const sidecarOpen = useSidecarOpen()
  const sidecarWaiting = useSidecarWaiting()
  // The dating app shows a download badge until the user has set it up (src/features/dating).
  const datingInstalled = useQuery({ queryKey: ['dating-status'], queryFn: () => api<{ installed: boolean }>('/dating/status') }).data?.installed ?? true
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">Skip to content</a>
      <AppNav view={view} go={go} storyOn={storyOn} datingInstalled={datingInstalled} unread={unread} sidecarOpen={sidecarOpen} sidecarWaiting={sidecarWaiting} />
      <main id="main" className="app-main" tabIndex={-1}>
        <DebugBanner onOpen={() => go('settings/debug')} />
        {companion.isPending ? <Loading label="Opening your companion" />
          : companion.isError ? <ErrorNotice error={companion.error} />
            : <Suspense fallback={<Loading label="Opening" />}><CurrentView view={view} companion={companion.data ?? null} go={go} openTab={openTab} /></Suspense>}
      </main>
      {sidecarOpen && <SidecarHost view={view} go={go} />}
      <AiNotice />
    </div>
  )
}

/** The sidecar docked beside the app, or in its own window (src/features/sidecar/popout.ts). */
function SidecarHost({ view, go }: { view: View; go: (view: View) => void }) {
  const mode = useSidecarMode()
  return (
    <Suspense fallback={null}>
      {mode === 'window' ? <SidecarWindow><Sidecar view={view} go={go} windowed /></SidecarWindow> : <Sidecar view={view} go={go} />}
    </Suspense>
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
  return view === 'chats' || view === 'worlds' || view === 'settings' || view.startsWith('settings/') || view === 'story' || view === 'dating' || view.startsWith('match/')
    || view === 'groups' || view.startsWith('group/')
}

function WorkspaceView({ view, companion, go, openTab }: CurrentViewProps) {
  const storyOn = useWorkspaceSettings().data?.story_mode
  if (view === 'chats') return <ChatsHome go={go} />
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
  if (fromToday(view)) return view === 'people' ? <WhoKnowsWho go={go} /> : <CityMap companion={companion} place={view.startsWith('map/') ? decodeURIComponent(view.slice(4)) : null} go={go} />
  if (view === 'memories') return <Memories companion={companion} />
  return <Conversation companion={companion} go={go} />
}
