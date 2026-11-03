import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ExternalLink, RefreshCw } from 'lucide-react'
import { SETTINGS_KEY, pcTimezone } from '../../companion'
import { api } from '../../api'
import type { UpdateCheck as Found, WorkspaceSettings as Settings } from '../../types'
import { Notice } from '../../components/Feedback'
import { RowGroup, SettingRow, SwitchRow } from '../../components/Rows'
import { timezones } from '../character/definition'
import { CHAT_STYLES } from '../conversation/chatStyles'
import { StyleThumb } from '../conversation/ChatMenu'
import { useChatStyle } from '../conversation/useChatStyle'
import { DEFAULT_OOC_MARKERS } from '../conversation/ooc'
import { usePhoneStatus } from '../phone/phoneAccess'
import { ColorSchemeSettings } from './ColorSchemeSettings'
import { DeviceLookSettings } from './DeviceLookSettings'
import { COMMUNITY_URL } from './CommunityLink'
import { howToUpdate, linkLabel, releasedOn } from './updateText'
import { OocMarkers, SectionError } from './WorkspaceSettings'
import { useWorkspace, type Save } from './useWorkspace'

/**
 * Settings > General (style guide): one row per setting, name on the left and its control on the right, with the
 * reasons behind a "?" where a value follows a rule. Chat style is a row of small pictures. The version and the
 * community link close the page.
 */
export function GeneralSettings() {
  const { data, save, setError, setPending, problem } = useWorkspace()
  if (!data) return <SectionError problem={problem} />
  return <>
    <SectionError problem={problem} />
    <RowGroup id="time-heading"><TimeZoneRow data={data} save={save} /></RowGroup>
    <ChatStyleRows />
    <WorldRows data={data} save={save} onPaused={(saved) => setPending({ paused: saved.paused, paused_at: saved.paused_at })} onError={setError} />
    <OocRows data={data} save={save} />
    <AboutRows />
  </>
}

const FOLLOW_PC = '__pc__'

/** Their time zone, following this PC unless the user picks one; the value says which ("Follow this PC (UTC)"). */
function TimeZoneRow({ data, save }: { data: Settings; save: Save }) {
  const client = useQueryClient()
  const pc = pcTimezone(data)
  const following = data.user_timezone_source === 'pc' && (!pc || data.user_timezone === pc)
  const zones = timezones()
  const choose = (value: string) => void save(value === FOLLOW_PC ? { user_timezone: pc!, user_timezone_source: 'pc' } : { user_timezone: value, user_timezone_source: 'chosen' })
    .then((saved) => { if (saved) void client.invalidateQueries({ queryKey: ['today'] }) })
  return (
    <SettingRow label="Time zone" tip="Used for dates, quiet hours and what time it is for you. Picking one keeps it put if this PC's time zone changes.">
      {(id) => (
        <select id={id} value={following ? FOLLOW_PC : data.user_timezone} onChange={(event) => choose(event.target.value)}>
          {pc && <option value={FOLLOW_PC}>Follow this PC ({pc})</option>}
          {!zones.includes(data.user_timezone) && <option value={data.user_timezone}>{data.user_timezone}</option>}
          {zones.map((zone) => <option key={zone} value={zone}>{zone}</option>)}
        </select>
      )}
    </SettingRow>
  )
}

/** The five chat styles as small pictures, with Retro IM's own two switches under it while it is picked; then the
 * app's colors and this device's text, font and motion. */
function ChatStyleRows() {
  const chat = useChatStyle()
  const [error, setError] = useState<string | null>(null)
  const save = async (change: Parameters<typeof chat.save>[0]) => setError(await chat.save(change))
  return (
    <section className="settings-section form-stack" aria-labelledby="appearance-heading">
      <h2 id="appearance-heading" className="section-title">Chat style</h2>
      {error && <Notice tone="error">{error}</Notice>}
      <div className="style-tiles" role="radiogroup" aria-labelledby="appearance-heading">
        {CHAT_STYLES.map((style) => (
          <button key={style.id} type="button" role="radio" aria-checked={chat.style === style.id} className="style-tile" title={style.description} onClick={() => void save({ chat_style: style.id })}>
            <StyleThumb style={style.id} /><span>{style.label}</span>
          </button>
        ))}
      </div>
      {chat.style === 'retro' && <RowGroup>
        <SwitchRow label="Retro IM sounds" tip="A chime for each new reply." checked={chat.soundsSetting} onChange={(checked) => void save({ chat_sounds: checked })} />
        <SwitchRow label="Retro IM dark mode" checked={chat.retroDarkSetting} onChange={(checked) => void save({ chat_retro_dark: checked })} />
      </RowGroup>}
      <RowGroup>
        <SwitchRow label="Period words in period cities" tip="In cities of another time, chats, posts and calls use that era's words. Settings always use today's." checked={chat.periodWords} onChange={(checked) => void save({ period_words: checked })} />
        <SwitchRow label="Keep my colors everywhere" tip="Companions' own colors and name fonts stay out of every chat. Your colors and reading font are used everywhere." checked={chat.keepMyColours} onChange={(checked) => void save({ keep_my_colours: checked })} />
      </RowGroup>
      <ColorSchemeSettings theme={chat.theme} scheme={chat.scheme} palette={chat.palette} save={save} />
      <DeviceLookSettings />
    </section>
  )
}

interface WorldRowsProps { data: Settings; save: Save; onPaused: (saved: Settings) => void; onError: (message: string) => void }

/** Whether the world moves on: the model's help in the background, and Pause. */
function WorldRows({ data, save, onPaused, onError }: WorldRowsProps) {
  const client = useQueryClient()
  const pause = async (paused: boolean) => {
    try {
      const saved = await api<Settings>(paused ? '/pause' : '/resume', {})
      onPaused(saved)
      client.setQueryData(SETTINGS_KEY, saved)
      void client.invalidateQueries({ queryKey: ['today'] })
    } catch (failure) { onError(failure instanceof Error ? failure.message : 'That did not work.') }
  }
  const since = data.paused && data.paused_at ? ` Paused since ${new Date(data.paused_at).toLocaleString()}.` : ''
  return (
    <RowGroup id="background-heading">
      <SwitchRow label="Use your model in the background" checked={data.background_activity} onChange={(value) => void save({ background_activity: value })}
        tip="Their life goes on either way while the Companion is running, built by rules with no model calls. On: your model also words those moments, prepares upcoming ones and looks up the weather and what's on. Nothing runs while the app is closed." />
      <span id="activity-heading" className="visually-hidden">Pause</span>
      <SwitchRow label="Pause this world" checked={data.paused} onChange={(value) => void pause(value)}
        tip={`Stops background work and life events here. You can still talk, and resuming skips the paused time rather than filling it in.${since}`} />
    </RowGroup>
  )
}

/** Asides marked out of character go to the sidecar, never to the companion; its markers are nested rows under it. */
function OocRows({ data, save }: { data: Settings; save: Save }) {
  const on = data.ooc_to_helper ?? true
  const markers = data.ooc_markers?.length ? data.ooc_markers : DEFAULT_OOC_MARKERS
  return (
    <RowGroup id="ooc-heading">
      <SwitchRow label="Out-of-character messages to the sidecar" checked={on} onChange={(value) => void save({ ooc_to_helper: value })}
        tip="Messages that start with OOC:, or the parts inside (( )), go to the sidecar instead of the character, and stay out of the chat. Off: the character answers them honestly." />
      <OocMarkers markers={markers} disabled={!on} save={(next) => void save({ ooc_markers: next })} />
    </RowGroup>
  )
}

/** The version with Check for updates (it asks GitHub only when pressed; nothing about you is sent), and the
 * community Discord. */
function AboutRows() {
  const health = useQuery({ queryKey: ['health'], queryFn: () => api<{ version: string }>('/health'), staleTime: Infinity })
  const [found, setFound] = useState<Found | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const check = async () => {
    if (busy) return
    setBusy(true)
    setError(null)
    try { setFound(await api<Found>('/updates/check', {})) } catch (failure) {
      setFound(null)
      setError(failure instanceof Error ? failure.message : 'The check did not finish.')
    } finally { setBusy(false) }
  }
  const version = found?.current ?? health.data?.version
  return <>
    <RowGroup id="updates-heading">
      <div className="setting-row">
        <span className="setting-row-label">{version ? `Version ${version}` : 'Version'}</span>
        <button type="button" className="text-button" aria-disabled={busy} title="Asks GitHub for the newest release. Nothing about you is sent." onClick={() => void check()}>
          <RefreshCw size={15} aria-hidden="true" className={busy ? 'spin' : undefined} />{busy ? 'Checking…' : 'Check for updates'}
        </button>
      </div>
      <a className="setting-row settings-link-row" href={COMMUNITY_URL} target="_blank" rel="noreferrer noopener">
        <span className="setting-row-label">Dreamers AI Hub<span className="visually-hidden"> (Discord, opens in a new tab)</span></span><ExternalLink aria-hidden="true" />
      </a>
    </RowGroup>
    <div aria-live="polite">
      {error && <Notice tone="error">{error}</Notice>}
      {found && <UpdateResult found={found} />}
    </div>
  </>
}

function UpdateResult({ found }: { found: Found }) {
  const onPhone = !!usePhoneStatus().data?.remote
  const link = (
    <a className="text-button" href={found.page} target="_blank" rel="noreferrer noopener">
      {linkLabel(found, onPhone)}<span className="visually-hidden"> (GitHub, opens in a new tab)</span>
    </a>
  )
  if (found.status === 'current') return <Notice tone="success" action={link}>You have the latest version.</Notice>
  if (found.status === 'unavailable') return <Notice tone="warning" action={link}>GitHub could not be reached just now. Try again later, or look at the releases page yourself.</Notice>
  return <Notice action={link}>Version {found.latest} is out{releasedOn(found.published)}. {howToUpdate(found, onPhone)}</Notice>
}
