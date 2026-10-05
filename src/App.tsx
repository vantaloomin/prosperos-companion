import { useCallback, useEffect, useRef, useState } from 'react'
import { BookHeart, CalendarDays, MessageCircle, Newspaper, Settings as SettingsIcon, UserRound } from 'lucide-react'
import type { Companion } from './types'
import { useCompanion, useFollowPcTimezone, type View } from './companion'
import { Conversation } from './features/conversation/Conversation'
import { Character } from './features/character/Character'
import { Appearance } from './features/appearance/Appearance'
import { Memories } from './features/memories/Memories'
import { Settings } from './features/settings/Settings'
import { Today } from './features/today/Today'
import { Feed } from './features/feed/Feed'
import { useReconcile } from './features/today/useReconcile'
import { useNotifications } from './features/notifications/useNotifications'
import { Loading, Notice } from './components/Feedback'

const VIEWS: { id: View; label: string; icon: typeof MessageCircle }[] = [
  { id: 'conversation', label: 'Chat', icon: MessageCircle },
  { id: 'today', label: 'Today', icon: CalendarDays },
  { id: 'feed', label: 'Feed', icon: Newspaper },
  { id: 'memories', label: 'Memories', icon: BookHeart },
  { id: 'character', label: 'Character', icon: UserRound },
  { id: 'settings', label: 'Settings', icon: SettingsIcon },
]

function viewFromHash(): View {
  const id = window.location.hash.slice(1)
  return VIEWS.some((view) => view.id === id) || id === 'appearance' ? id as View : 'conversation'
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
  useNotifications(!!companion.data, go)
  useFocusOnViewChange(view)
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">Skip to content</a>
      <nav className="app-nav" aria-label="Views">
        {VIEWS.map(({ id, label, icon: Icon }) => (
          <button key={id} type="button" aria-current={view === id || (id === 'character' && view === 'appearance') ? 'page' : undefined} onClick={() => go(id)}>
            <Icon aria-hidden="true" /><span>{label}</span>
          </button>
        ))}
      </nav>
      <main id="main" className="app-main" tabIndex={-1}>
        {companion.isPending ? <Loading label="Opening your companion" />
          : companion.isError ? <Notice tone="error">{companion.error.message}</Notice>
            : <CurrentView view={view} companion={companion.data ?? null} go={go} />}
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

function CurrentView({ view, companion, go }: { view: View; companion: Companion | null; go: (view: View) => void }) {
  if (view === 'settings') return <Settings companion={companion} />
  if (view === 'character') return <Character companion={companion} go={go} />
  if (!companion) return <Welcome go={go} />
  if (view === 'appearance') return <Appearance companion={companion} go={go} />
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
