import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import { Search } from 'lucide-react'
import type { Companion } from '../../types'
import { Backups } from './Backups'
import { ChatStyleSettings } from './ChatStyleSettings'
import { ContextSettings } from './ContextSettings'
import { ImageSettings } from './ImageSettings'
import { LifeSettings } from './LifeSettings'
import { NotificationSettings } from './NotificationSettings'
import { PhoneSettings } from './PhoneSettings'
import { PromptSettings } from './PromptSettings'
import { BackgroundSettings, MemorySettings, PauseSettings, RestoredReview, TimezoneSettings } from './WorkspaceSettings'
import { Cities } from '../world/Cities'
import { ModelSettings } from './models/ModelSettings'
import { usePhoneStatus } from '../phone/phoneAccess'
import { availableTabs, pickTab, searchSettings, type SettingsMatch, type SettingsTab } from './sections'

interface Props {
  companion: Companion | null
  /** The tab named in the address (#settings/models); an unknown or unavailable one opens the first tab. */
  tab?: string
  onTab: (tab: SettingsTab) => void
}

export function Settings({ companion, tab, onTab }: Props) {
  const onPhone = !!usePhoneStatus().data?.remote
  const current = pickTab(tab, !!companion, onPhone)
  const landing = useLanding()
  const land = (match: SettingsMatch) => { onTab(match.tab.id); landing(match.section.heading) }
  return (
    <section className="page settings">
      <header className="page-header"><h1>Settings</h1></header>
      {companion && <RestoredReview onDone={() => { onTab('memory'); landing('memory-heading') }} />}
      <SettingsSearch hasCompanion={!!companion} onPhone={onPhone} onPick={land} />
      <div className="settings-layout">
        <SettingsTabs current={current} hasCompanion={!!companion} onPhone={onPhone} onTab={onTab} />
        <div className="settings-panel" role="tabpanel" id={`settings-panel-${current}`} aria-labelledby={`settings-tab-${current}`}>
          <TabContent tab={current} companion={companion} />
        </div>
      </div>
    </section>
  )
}

/**
 * Moves focus to a section heading, for a search result or a finished review. The heading only
 * exists once its tab and that section's data have rendered, so it keeps looking for a moment.
 */
function useLanding() {
  const frame = useRef(0)
  useEffect(() => () => cancelAnimationFrame(frame.current), [])
  return (id: string) => {
    cancelAnimationFrame(frame.current)
    const until = performance.now() + 3000
    const attempt = () => {
      const heading = document.getElementById(id)
      if (!heading) { if (performance.now() < until) frame.current = requestAnimationFrame(attempt); return }
      if (!heading.hasAttribute('tabindex')) heading.setAttribute('tabindex', '-1')
      heading.focus()
    }
    frame.current = requestAnimationFrame(attempt)
  }
}

function TabContent({ tab, companion }: { tab: SettingsTab; companion: Companion | null }) {
  const name = companion?.version.name ?? ''
  const content: Record<SettingsTab, ReactNode> = {
    general: <><TimezoneSettings /><ChatStyleSettings /><PauseSettings /><BackgroundSettings /></>,
    models: <><ModelSettings /><PromptSettings /></>,
    life: <><LifeSettings name={name} /><Cities /></>,
    memory: <MemorySettings />,
    lookups: <ContextSettings name={name} />,
    images: <ImageSettings />,
    notifications: <NotificationSettings />,
    phone: <PhoneSettings />,
    data: <Backups />,
  }
  return content[tab]
}

const NEXT_KEYS: Record<string, number> = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }

/** Vertical tabs beside the panel on wide windows, a scrolling row above it on narrow ones. */
function SettingsTabs({ current, hasCompanion, onPhone, onTab }: { current: SettingsTab; hasCompanion: boolean; onPhone: boolean; onTab: (tab: SettingsTab) => void }) {
  const tabs = availableTabs(hasCompanion, onPhone)
  const narrow = useNarrow()
  const list = useRef<HTMLDivElement>(null)
  // On a narrow window the row scrolls; keep the open tab in sight, as after a deep link.
  useEffect(() => { list.current?.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: 'nearest', inline: 'nearest' }) }, [current])
  // Arrow keys move between tabs and open them, Home and End jump to the ends (the WAI-ARIA tabs pattern).
  const onKeyDown = (event: KeyboardEvent) => {
    const index = tabs.findIndex((item) => item.id === current)
    const target = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1
      : event.key in NEXT_KEYS ? (index + NEXT_KEYS[event.key] + tabs.length) % tabs.length : null
    if (target === null) return
    event.preventDefault()
    onTab(tabs[target].id)
    list.current?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[target]?.focus()
  }
  return (
    <div className="settings-tabs" role="tablist" aria-label="Settings" aria-orientation={narrow ? 'horizontal' : 'vertical'} ref={list} onKeyDown={onKeyDown}>
      {tabs.map((item) => (
        <button key={item.id} type="button" role="tab" id={`settings-tab-${item.id}`} aria-selected={item.id === current}
          aria-controls={item.id === current ? `settings-panel-${item.id}` : undefined} tabIndex={item.id === current ? 0 : -1} onClick={() => onTab(item.id)}>
          {item.label}
        </button>
      ))}
    </div>
  )
}

const NARROW = '(max-width: 720px)'

function useNarrow() {
  const [narrow, setNarrow] = useState(() => window.matchMedia(NARROW).matches)
  useEffect(() => {
    const query = window.matchMedia(NARROW)
    const sync = () => setNarrow(query.matches)
    query.addEventListener('change', sync)
    return () => query.removeEventListener('change', sync)
  }, [])
  return narrow
}

function SettingsSearch({ hasCompanion, onPhone, onPick }: { hasCompanion: boolean; onPhone: boolean; onPick: (match: SettingsMatch) => void }) {
  const [query, setQuery] = useState('')
  const matches = searchSettings(query, hasCompanion, onPhone)
  const searching = query.trim().length > 0
  return (
    <div className="settings-search">
      <label className="visually-hidden" htmlFor="settings-search">Find a setting</label>
      <div className="search-field">
        <Search aria-hidden="true" />
        <input id="settings-search" type="search" placeholder="Find a setting" value={query} onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => { if (event.key === 'Escape') setQuery('') }} aria-describedby="settings-search-count" />
      </div>
      <p id="settings-search-count" className="visually-hidden" aria-live="polite">{searching ? `${matches.length} ${matches.length === 1 ? 'setting' : 'settings'} found` : ''}</p>
      {searching && (matches.length ? (
        <ul className="settings-results">
          {matches.map((match) => (
            <li key={match.section.heading}>
              <button type="button" className="text-button" onClick={() => { setQuery(''); onPick(match) }}>
                {match.section.title}{match.section.title !== match.tab.label && <span className="subtle"> in {match.tab.label}</span>}
              </button>
            </li>
          ))}
        </ul>
      ) : <p className="subtle settings-results">No settings match “{query.trim()}”.</p>)}
    </div>
  )
}
