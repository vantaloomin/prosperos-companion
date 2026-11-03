import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import { ChevronLeft, ChevronRight, Search } from 'lucide-react'
import type { Companion } from '../../types'
import { StoryModeSetting } from './StoryModeSetting'
import { ModelCalls } from './ModelCalls'
import { Backups } from './Backups'
import { DataFolder } from './DataFolder'
import { DebugSettings } from './DebugSettings'
import { TownsfolkMix } from './TownsfolkMix'
import { DebugMatches } from './DebugMatches'
import { ImageSettings } from './ImageSettings'
import { RealismPage } from './RealismPage'
import { SUB_PAGES, subFor, type RealismSub, type WorldSub } from './subPages'
import { WorldPage } from './WorldPage'
import { InfoTip } from '../../components/InfoTip'
import { NotificationSettings } from './NotificationSettings'
import { PhoneSettings } from './PhoneSettings'
import { PromptSettings } from './PromptSettings'
import { usePhone } from '../../components/usePhone'
import { MemorySettings, RestoredReview } from './WorkspaceSettings'
import { GeneralSettings } from './GeneralSettings'
import { BuiltinRecall } from './models/BuiltinRecall'
import { VoiceSettings } from './models/VoiceSettings'
import { HardwareCheck } from './models/HardwareCheck'
import { LocalPrograms } from './models/LocalPrograms'
import { ModelSettings } from './models/ModelSettings'
import { usePhoneStatus } from '../phone/phoneAccess'
import { NextStep } from './NextStep'
import { availableTabs, pickTab, searchSettings, type SettingsMatch, type SettingsTab } from './sections'

interface Props {
  companion: Companion | null
  /** The tab named in the address (#settings/models); an unknown or unavailable one opens the first tab. */
  tab?: string
  onTab: (tab: SettingsTab) => void
  /** On a phone, back from a group to the list of groups. */
  onHome?: () => void
  /** Before there is a companion: where "create your companion" goes once a model is connected. */
  onCreate?: () => void
}

/**
 * Settings (style guide: Settings): eight groups and Advanced, last under a line. A wide window lists them beside the
 * open one with Find a setting above; a phone opens on the list of groups, like a phone's own settings, and each group
 * has a way back.
 */
export function Settings({ companion, tab, onTab, onHome, onCreate }: Props) {
  const onPhone = !!usePhoneStatus().data?.remote
  const small = usePhone()
  const landing = useLanding()
  // Realism keeps some sections on pages of their own; the open one titles the page and is where back goes first.
  const [sub, setSub] = useState<string | null>(null)
  const openTab = (next: SettingsTab) => { setSub(null); onTab(next) }
  const land = (match: SettingsMatch) => {
    setSub(subFor(match.tab.id, match.section.heading))
    onTab(match.tab.id)
    landing(match.section.heading)
  }
  const search = <SettingsSearch hasCompanion={!!companion} onPhone={onPhone} onPick={land} />
  const next = !companion && onCreate ? <NextStep onCreate={onCreate} /> : null
  if (small && !tab) {
    return (
      <section className="page settings settings-home">
        <header className="page-header"><h1>Settings</h1></header>
        {next}{search}
        <SettingsList hasCompanion={!!companion} onPhone={onPhone} onTab={openTab} />
      </section>
    )
  }
  const current = pickTab(tab, !!companion, onPhone)
  return <SettingsPanel {...{ companion, current, small, onPhone, next, search, sub, setSub, onHome }} onTab={openTab}
    onReviewed={() => { onTab('memory'); landing('memory-heading') }} />
}

interface PanelProps {
  companion: Companion | null; current: SettingsTab; small: boolean; onPhone: boolean; next: ReactNode; search: ReactNode
  sub: string | null; setSub: (sub: string | null) => void; onTab: (tab: SettingsTab) => void; onHome?: () => void; onReviewed: () => void
}

/** An open group: its title and way back, the groups beside it on a wide window, and its settings. */
function SettingsPanel({ companion, current, small, onPhone, next, search, sub, setSub, onTab, onHome, onReviewed }: PanelProps) {
  const page = openPage(current, sub)
  const head = <PanelHead small={small} label={tabLabel(current, !!companion, onPhone)} page={page} onBack={page ? () => setSub(null) : onHome} />
  const labelledBy = small ? (page?.heading ?? 'settings-tab-phone') : `settings-tab-${current}`
  return (
    <section className="page settings">
      {small && head}
      {next}
      {companion && <RestoredReview onDone={onReviewed} />}
      <div className="settings-layout">
        {!small && <nav className="settings-nav" aria-label="Settings groups">
          {search}
          <SettingsTabs current={current} hasCompanion={!!companion} onPhone={onPhone} onTab={onTab} />
        </nav>}
        <div className="settings-panel" role="tabpanel" id={`settings-panel-${current}`} aria-labelledby={labelledBy}>
          {!small && head}
          <TabContent tab={current} companion={companion} pages={{ sub, open: setSub }} />
        </div>
      </div>
    </section>
  )
}

/** The page of its own open within a group, if any (Realism and World have them). */
function openPage(tab: SettingsTab, sub: string | null) {
  return sub ? SUB_PAGES[tab]?.[sub] ?? null : null
}

function tabLabel(tab: SettingsTab, hasCompanion: boolean, onPhone: boolean): string {
  return availableTabs(hasCompanion, onPhone).find((item) => item.id === tab)?.label ?? 'Settings'
}

interface PanelHeadProps { small: boolean; label: string; page: { title: string; tip: string; heading: string } | null; onBack?: () => void }

/**
 * One title and one way back per level (Iris): the open group's name, or the open page's within it with its "?".
 * On a phone the header's back goes up one level; on a wide window the groups are beside it, and a page has a small
 * link back to its group above the title.
 */
function PanelHead({ small, label, page, onBack }: PanelHeadProps) {
  const title = <h1 id={page ? page.heading : small ? 'settings-tab-phone' : undefined} className={small ? undefined : 'settings-head'}>
    {page?.title ?? label}{page && <InfoTip id={`${page.heading}-tip`} label={page.title} text={page.tip} />}
  </h1>
  if (small) {
    return <header className="settings-phone-head">
      <button type="button" className="icon-button" aria-label={page ? `Back to ${label}` : 'All settings'} onClick={onBack}><ChevronLeft aria-hidden="true" /></button>{title}
    </header>
  }
  return page ? <div className="settings-subhead"><button type="button" className="text-button settings-back" onClick={onBack}><ChevronLeft aria-hidden="true" />{label}</button>{title}</div> : title
}

/** A phone's Settings: every group as a row that opens it, Advanced last under a line. */
function SettingsList({ hasCompanion, onPhone, onTab }: { hasCompanion: boolean; onPhone: boolean; onTab: (tab: SettingsTab) => void }) {
  const tabs = availableTabs(hasCompanion, onPhone)
  const row = (item: (typeof tabs)[number]) => (
    <button key={item.id} type="button" className="setting-row settings-group-row" onClick={() => onTab(item.id)}>
      <span className="setting-row-label">{item.label}</span><ChevronRight aria-hidden="true" />
    </button>
  )
  return <>
    <div className="row-list">{tabs.filter((item) => !item.advanced).map(row)}</div>
    {tabs.some((item) => item.advanced) && <div className="row-list">{tabs.filter((item) => item.advanced).map(row)}</div>}
  </>
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

function TabContent({ tab, companion, pages }: { tab: SettingsTab; companion: Companion | null; pages: { sub: string | null; open: (sub: string) => void } }) {
  const name = companion?.version.name ?? ''
  // Built-in recall reads and runs files on the PC, so a phone does not show it (companion/phone/access.py).
  const remote = !!usePhoneStatus().data?.remote
  const content: Record<SettingsTab, ReactNode> = {
    general: <GeneralSettings />,
    models: <>{!remote && <HardwareCheck />}<ModelSettings />{!remote && <LocalPrograms />}{!remote && <BuiltinRecall />}<VoiceSettings /></>,
    world: <WorldPage name={name} sub={pages.sub as WorldSub | null} open={pages.open} />,
    realism: <RealismPage name={name} sub={pages.sub as RealismSub | null} open={pages.open} />,
    memory: <MemorySettings />,
    pictures: <ImageSettings />,
    devices: <><NotificationSettings /><PhoneSettings /></>,
    data: <>{!remote && <DataFolder />}<Backups /><DebugSettings name={name} />{!remote && <><ModelCalls /><TownsfolkMix /><DebugMatches /></>}</>,
    advanced: <><StoryModeSetting /><PromptSettings /></>,
  }
  return content[tab]
}

const NEXT_KEYS: Record<string, number> = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }

/** The groups beside the open one on a wide window, Advanced last under a line. */
function SettingsTabs({ current, hasCompanion, onPhone, onTab }: { current: SettingsTab; hasCompanion: boolean; onPhone: boolean; onTab: (tab: SettingsTab) => void }) {
  const tabs = availableTabs(hasCompanion, onPhone)
  const list = useRef<HTMLDivElement>(null)
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
    <div className="settings-tabs" role="tablist" aria-label="Settings" aria-orientation="vertical" ref={list} onKeyDown={onKeyDown}>
      {tabs.map((item) => (
        <button key={item.id} type="button" role="tab" className={item.advanced ? 'settings-tab-apart' : undefined} id={`settings-tab-${item.id}`} aria-selected={item.id === current}
          aria-controls={item.id === current ? `settings-panel-${item.id}` : undefined} tabIndex={item.id === current ? 0 : -1} onClick={() => onTab(item.id)}>
          {item.label}
        </button>
      ))}
    </div>
  )
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
        <input autoComplete="off" id="settings-search" type="search" placeholder="Find a setting" value={query} onChange={(event) => setQuery(event.target.value)}
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
