import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react'
import { BookHeart, BookOpen, CalendarDays, Settings as SettingsIcon, UserRound } from 'lucide-react'
import type { Companion } from './types'
import { useCompanion, useFollowPcTimezone, useWorkspaceSettings, type View } from './companion'
import { Conversation } from './features/conversation/Conversation'
import type { SettingsTab } from './features/settings/sections'
import { useReconcile } from './features/today/useReconcile'
import { useNotifications } from './features/notifications/useNotifications'
import { useTexts } from './features/conversation/useTexts'
import { Loading, Notice } from './components/Feedback'
import { DebugBanner } from './features/settings/DebugBanner'
import { Profile } from './features/profile/Profile'
import { profileTab } from './features/profile/profileText'

// Chat opens first, so it ships in the main bundle; every other view loads the first time it is opened.
const Character = lazy(() => import('./features/character/Character').then((m) => ({ default: m.Character })))
const SwitchTo = lazy(() => import('./features/character/SwitchTo').then((m) => ({ default: m.SwitchTo })))
const Appearance = lazy(() => import('./features/appearance/Appearance').then((m) => ({ default: m.Appearance })))
const Portraits = lazy(() => import('./features/appearance/Portraits').then((m) => ({ default: m.Portraits })))
const Memories = lazy(() => import('./features/memories/Memories').then((m) => ({ default: m.Memories })))
const Settings = lazy(() => import('./features/settings/Settings').then((m) => ({ default: m.Settings })))
const Today = lazy(() => import('./features/today/Today').then((m) => ({ default: m.Today })))
const Story = lazy(() => import('./features/story/Story').then((m) => ({ default: m.Story })))
const Feed = lazy(() => import('./features/feed/Feed').then((m) => ({ default: m.Feed })))

// The companion's profile holds the chat (Messages), the feed (Posts) and the character as tabs.
const VIEWS: { id: View; label: string; icon: typeof UserRound }[] = [
  { id: 'conversation', label: 'Profile', icon: UserRound },
  { id: 'story', label: 'Story', icon: BookOpen },
  { id: 'today', label: 'Today', icon: CalendarDays },
  { id: 'memories', label: 'Memories', icon: BookHeart },
  { id: 'settings', label: 'Settings', icon: SettingsIcon },
]

function viewFromHash(): View {
  const id = window.location.hash.slice(1)
  return VIEWS.some((view) => view.id === id) || profileTab(id) || id.startsWith('settings/') ? id as View : 'conversation'
}

function isCurrent(id: View, view: View) {
  return view === id || (id === 'conversation' && profileTab(view) !== null) || (id === 'settings' && view.startsWith('settings/'))
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
  useFocusOnViewChange(view)
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">Skip to content</a>
      <nav className="app-nav" aria-label="Views">
        {VIEWS.map(({ id, label, icon: Icon }) => (
          <button key={id} type="button" aria-current={isCurrent(id, view) ? 'page' : undefined} onClick={() => go(id)}>
            <Icon aria-hidden="true" /><span>{label}</span>
          </button>
        ))}
      </nav>
      <main id="main" className="app-main" tabIndex={-1}>
        <DebugBanner onOpen={() => go('settings/debug')} />
        {companion.isPending ? <Loading label="Opening your companion" />
          : companion.isError ? <Notice tone="error">{companion.error.message}</Notice>
            : <Suspense fallback={<Loading label="Opening" />}><CurrentView view={view} companion={companion.data ?? null} go={go} openTab={openTab} /></Suspense>}
      </main>
    </div>
  )
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
  // Settings and the story belong to the workspace, so they open with or without a companion.
  if (inWorkspace(view)) return <WorkspaceView view={view} companion={companion} go={go} openTab={openTab} />
  // With the LoRA creator switched off (the default), an old #appearance link opens the Character page.
  const shown = view === 'appearance' && !loraMaker ? 'character' : view
  if (!companion) return shown === 'character' ? <Character companion={null} go={go} /> : <Welcome go={go} />
  const page = shown === 'character' ? <Character companion={companion} go={go} /> : <CompanionView view={shown} companion={companion} go={go} />
  return profileTab(shown) ? <Profile companion={companion} view={shown} go={go}>{page}</Profile> : page
}

function inWorkspace(view: View) {
  return view === 'settings' || view.startsWith('settings/') || view === 'story'
}

function WorkspaceView({ view, companion, go, openTab }: CurrentViewProps) {
  return view === 'story' ? <Story go={go} /> : <Settings companion={companion} tab={view.split('/')[1]} onTab={openTab} />
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

function Welcome({ go }: { go: (view: View) => void }) {
  return (
    <section className="welcome">
      <p className="eyebrow">Prospero Companion</p>
      <h1>Meet someone new</h1>
      <p className="lede">Start by creating your companion: who they are, how they talk, and what kind of relationship you want. You can talk as soon as a model is connected, and change everything later.</p>
      <button type="button" className="button primary" onClick={() => go('character')}>Create your companion</button>
    </section>
  )
}
