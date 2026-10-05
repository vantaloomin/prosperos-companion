import { useEffect, useState } from 'react'
import { BookHeart, CalendarDays, MessageCircle, Newspaper, Settings as SettingsIcon, UserRound } from 'lucide-react'
import type { Companion } from './types'
import { useCompanion, type View } from './companion'
import { Conversation } from './features/conversation/Conversation'
import { Character } from './features/character/Character'
import { Memories } from './features/memories/Memories'
import { Settings } from './features/settings/Settings'
import { Today } from './features/today/Today'
import { useReconcile } from './features/today/useReconcile'
import { Placeholder } from './components/Placeholder'
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
  return VIEWS.some((view) => view.id === id) ? id as View : 'conversation'
}

export default function App() {
  const [view, setView] = useState<View>(viewFromHash)
  const companion = useCompanion()
  useReconcile(!!companion.data)
  useEffect(() => {
    const sync = () => setView(viewFromHash())
    window.addEventListener('popstate', sync)
    return () => window.removeEventListener('popstate', sync)
  }, [])
  const go = (next: View) => { window.history.pushState(null, '', `#${next}`); setView(next) }
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">Skip to content</a>
      <nav className="app-nav" aria-label="Views">
        {VIEWS.map(({ id, label, icon: Icon }) => (
          <button key={id} type="button" aria-current={view === id ? 'page' : undefined} onClick={() => go(id)}>
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

function CurrentView({ view, companion, go }: { view: View; companion: Companion | null; go: (view: View) => void }) {
  if (view === 'settings') return <Settings companion={companion} />
  if (view === 'character') return <Character companion={companion} go={go} />
  if (!companion) return <Welcome go={go} />
  if (view === 'today') return <Today companion={companion} go={go} />
  if (view === 'feed') return <Placeholder title="Feed" text={`${companion.version.name}'s private posts will appear here once the feed is ready.`} />
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
