import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { SETTINGS_KEY, pcTimezone, useWorkspaceSettings } from '../../companion'
import { Pause, Play, X } from 'lucide-react'
import { api } from '../../api'
import type { WorkspaceSettings as Settings } from '../../types'
import { Notice } from '../../components/Feedback'
import { TextInput, Toggle } from '../../components/Fields'
import { timezones } from '../character/definition'
import { DEFAULT_OOC_MARKERS, type OocMarker } from '../conversation/ooc'

type Save = (change: Partial<Settings> & { review_complete?: boolean }) => Promise<boolean>

/**
 * The workspace settings and a way to change them, shared by the sections on several Settings tabs.
 * Toggles show the new state at once and fall back to the saved state if the change is refused.
 */
function useWorkspace() {
  const client = useQueryClient()
  const settings = useWorkspaceSettings()
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<Partial<Settings>>({})
  const save: Save = async (change) => {
    setPending((current) => ({ ...current, ...change }))
    try {
      const saved = await api<Settings>('/settings', change, 'PUT')
      // Holding the saved values locally avoids a flicker before the shared cache re-renders. Only
      // the changed ones: other tabs' sections save the rest, and a stale copy here would hide them.
      setPending((current) => ({ ...current, ...pick(saved, change) }))
      client.setQueryData(SETTINGS_KEY, saved)
      setError(null)
      return true
    } catch (failure) {
      setPending({})
      setError(failure instanceof Error ? failure.message : 'That setting was not saved.')
      return false
    }
  }
  const data = settings.data ? { ...settings.data, ...pending } : null
  const problem = error ?? (settings.isError ? settings.error.message : null)
  return { data, save, setError, setPending, problem }
}

function pick(saved: Settings, change: Partial<Settings>): Partial<Settings> {
  return Object.fromEntries(Object.keys(change).filter((key) => key in saved).map((key) => [key, saved[key as keyof Settings]]))
}

function SectionError({ problem }: { problem: string | null }) {
  return problem ? <Notice tone="error">{problem}</Notice> : null
}

/** After a restore: shown above every tab, and finishing it lands on the memory settings it is about. */
export function RestoredReview({ onDone }: { onDone: () => void }) {
  const { data, save, problem } = useWorkspace()
  if (!data?.review_required) return null
  const complete = async () => { if (await save({ review_complete: true })) onDone() }
  return (
    <>
      <Notice action={<button type="button" className="text-button" onClick={() => void complete()}>Mark review complete</button>}>
        This workspace was restored from a backup. Look over its memories before turning on memory or background activity; a backup can hold things you asked to forget later.
      </Notice>
      <SectionError problem={problem} />
    </>
  )
}

export function PauseSettings() {
  const client = useQueryClient()
  const { data, setError, setPending, problem } = useWorkspace()
  if (!data) return <SectionError problem={problem} />
  const pause = async (paused: boolean) => {
    try {
      const saved = await api<Settings>(paused ? '/pause' : '/resume', {})
      setPending({ paused: saved.paused, paused_at: saved.paused_at })
      client.setQueryData(SETTINGS_KEY, saved)
      void client.invalidateQueries({ queryKey: ['today'] })
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'That did not work.') }
  }
  return (
    <section className="settings-section form-stack" aria-labelledby="activity-heading">
      <SectionError problem={problem} />
      <div>
        <h2 id="activity-heading">Pause</h2>
        <p className="subtle">{data.paused ? `Paused since ${new Date(data.paused_at!).toLocaleString()}. Nothing happens in your companion's life while paused, and resuming skips that time rather than filling it in.` : 'Pausing stops all background work and life events. You can still talk.'}</p>
      </div>
      <div className="form-actions">
        <button type="button" className="button" onClick={() => void pause(!data.paused)}>{data.paused ? <><Play aria-hidden="true" />Resume</> : <><Pause aria-hidden="true" />Pause</>}</button>
      </div>
    </section>
  )
}

export function BackgroundSettings() {
  const { data, save, problem } = useWorkspace()
  if (!data) return <SectionError problem={problem} />
  return (
    <section className="settings-section form-stack" aria-labelledby="background-heading">
      <h2 id="background-heading">Background activity</h2>
      <SectionError problem={problem} />
      <Toggle label="Use your model while the app is open in the background" checked={data.background_activity} onChange={(value) => void save({ background_activity: value })}
        hint="Their life goes on either way while the Companion is running, built by rules with no model calls. On: your model also words those moments, prepares upcoming ones and looks up the weather and what's on. Nothing runs while the app is closed." />
    </section>
  )
}

const ZONE_USE = 'Used for dates, quiet hours and what time it is for you.'
const ZONE_HINTS: Record<Settings['user_timezone_source'], string> = {
  pc: `Following this PC's timezone. ${ZONE_USE}`,
  chosen: `Set by you, so it stays put if this PC's timezone changes. ${ZONE_USE}`,
  default: ZONE_USE,
}

export function TimezoneSettings() {
  const { data, save, problem } = useWorkspace()
  if (!data) return <SectionError problem={problem} />
  return <TimezoneForm data={data} save={save} problem={problem} />
}

function TimezoneForm({ data, save, problem }: { data: Settings; save: Save; problem: string | null }) {
  const client = useQueryClient()
  const [zone, setZone] = useState<string | null>(null)
  const pc = pcTimezone(data)
  const edited = zone !== null && zone !== data.user_timezone
  const offerPc = !!pc && (zone !== null || `${data.user_timezone_source}:${data.user_timezone}` !== `pc:${pc}`)
  const savedZone = (change: Partial<Settings>) => void save(change).then((saved) => {
    if (saved) { setZone(null); void client.invalidateQueries({ queryKey: ['today'] }) }
  })
  const hint = ZONE_HINTS[data.user_timezone_source]
  return (
    <section className="settings-section form-stack" aria-labelledby="time-heading">
      <h2 id="time-heading">Your time</h2>
      <SectionError problem={problem} />
      <TextInput label="Your timezone" value={zone ?? data.user_timezone} onChange={setZone} list="settings-timezones" maxLength={64} hint={hint} />
      <datalist id="settings-timezones">{timezones().map((item) => <option key={item} value={item} />)}</datalist>
      {pc && <p className="subtle">This PC's timezone: {pc}</p>}
      {(edited || offerPc) && (
        <div className="form-actions">
          {edited && <button type="button" className="button primary" onClick={() => savedZone({ user_timezone: zone!, user_timezone_source: 'chosen' })}>Save timezone</button>}
          {offerPc && <button type="button" className="button" onClick={() => savedZone({ user_timezone: pc!, user_timezone_source: 'pc' })}>Use this PC's timezone</button>}
        </div>
      )}
    </section>
  )
}

export function MemorySettings() {
  const { data, save, problem } = useWorkspace()
  if (!data) return <SectionError problem={problem} />
  return (
        <section className="settings-section form-stack" aria-labelledby="memory-heading">
          <h2 id="memory-heading" tabIndex={-1}>Memory</h2>
          <SectionError problem={problem} />
          <Toggle label="Remember things automatically" checked={data.automatic_memory} onChange={(value) => void save({ automatic_memory: value })}
            hint="When on, facts you state directly in new messages (your name, where you live, a plan with a date) are saved with the messages they came from, after each reply. Questions, hypotheticals, quotes and roleplay are never saved. Earlier messages are not scanned. When off, only what you choose to remember is saved; your conversation is kept either way." />
          <Toggle label="Allow sensitive memories" checked={data.sensitive_memory} onChange={(value) => void save({ sensitive_memory: value })}
            hint="Health (like an allergy), beliefs, money and similar details are saved automatically with this on, so they can be remembered when it matters. Turn it off to have them wait in Memories as suggestions for you to keep or decline." />
          <Toggle label="Let the model catch more" checked={data.model_memory_suggestions ?? true} disabled={!data.automatic_memory}
            onChange={(value) => void save({ model_memory_suggestions: value })}
            hint="Messages the built-in rules found nothing in are sent to your model connection in the background, which picks out facts in your own words. They are saved automatically and marked that way in Memories, where you can correct or delete them; anything that contradicts a saved fact waits for you. Uses extra model time." />
          <Toggle label="Ask about people in your life" checked={data.ask_about_people ?? true} onChange={(value) => void save({ ask_about_people: value })}
            hint="People you mention (your sister, your boss, a friend by name) and what you say about them are remembered under the same setting as everything else. With this on, they may now and then ask how someone is doing or how their news turned out, at most once per question. Never after a loss, or about anyone a boundary covers." />
          <Toggle label="Let them look back when they need to" checked={data.recall_more ?? true} onChange={(value) => void save({ recall_more: value })}
            hint="When you bring up something from before that they can't place, they may take one more look through their memories and your earlier chats before answering. That reply can take up to twice as long. The app also widens its own search when the first look finds little; that needs no extra model time." />
          <Toggle label="Share what you've told them across alternate timelines" checked={data.share_profile_across_timelines} onChange={(value) => void save({ share_profile_across_timelines: value })}
            hint="Facts about you, your plans and how you're doing apply in every timeline, including ones you start with Edit from here. When off, each timeline only knows what you told it, plus what came before its edit. Shared moments and the companion's own life always stay in their own timeline." />
        </section>
  )
}

/** General > Out-of-character messages: asides marked like this go to the helper, never to the companion. */
export function OocSettings() {
  const { data, save, problem } = useWorkspace()
  if (!data) return <SectionError problem={problem} />
  const markers = data.ooc_markers?.length ? data.ooc_markers : DEFAULT_OOC_MARKERS
  return (
    <section className="settings-section form-stack" aria-labelledby="ooc-heading">
      <h2 id="ooc-heading">Out-of-character messages</h2>
      <SectionError problem={problem} />
      <Toggle label="Send out-of-character messages to the sidecar" checked={data.ooc_to_helper ?? true} onChange={(value) => void save({ ooc_to_helper: value })}
        hint="Messages that start with OOC:, or the parts inside (( )), go to the sidecar instead of the character, and stay out of the chat; the rest is sent as usual. Off: the character answers them honestly." />
      {(data.ooc_to_helper ?? true) && <OocMarkers markers={markers} save={(next) => void save({ ooc_markers: next })} />}
    </section>
  )
}

const sameMarkers = (a: OocMarker[], b: OocMarker[]) =>
  a.length === b.length && a.every((row, index) => row.open.toLowerCase() === b[index].open.toLowerCase() && row.close.toLowerCase() === b[index].close.toLowerCase())

/** What is wrong with one marker row, if anything. */
function markerProblem(rows: MarkerRow[], index: number): string | null {
  const row = rows[index]
  if (!row.open.trim() || (row.pair && !row.close.trim())) return 'A marker needs at least one character.'
  const same = (other: OocMarker) => other.open.trim().toLowerCase() === row.open.trim().toLowerCase() && other.close.trim().toLowerCase() === row.close.trim().toLowerCase()
  return rows.slice(0, index).some(same) ? 'That marker is already in the list.' : null
}

type MarkerRow = OocMarker & { pair: boolean }

function OocMarkers({ markers, save }: { markers: OocMarker[]; save: (markers: OocMarker[]) => void }) {
  const [rows, setRows] = useState<MarkerRow[]>(() => markers.map((row) => ({ ...row, pair: !!row.close })))
  const [adding, setAdding] = useState(false)
  // Saved as soon as every marker is complete; while one isn't, its row says why.
  const change = (next: MarkerRow[]) => {
    setRows(next)
    if (next.length && next.every((_row, index) => !markerProblem(next, index))) {
      save(next.map((row) => ({ open: row.open.trim(), close: row.pair ? row.close.trim() : '' })))
    }
  }
  const edit = (index: number, part: Partial<MarkerRow>) => change(rows.map((row, at) => (at === index ? { ...row, ...part } : row)))
  const add = (pair: boolean) => { setRows([...rows, { open: '', close: '', pair }]); setAdding(false) }
  return (
    <fieldset className="form-stack">
      <legend>Markers</legend>
      {rows.map((row, index) => (
        <MarkerRowEditor key={index} row={row} problem={markerProblem(rows, index)} only={rows.length < 2}
          onChange={(part) => edit(index, part)} onRemove={() => change(rows.filter((_, at) => at !== index))} />
      ))}
      <div className="form-actions">
        {adding
          ? <span role="group" aria-label="Kind of marker">
              <button type="button" className="button" onClick={() => add(false)}>Starts with</button>
              <button type="button" className="button" onClick={() => add(true)}>Between</button>
            </span>
          : <button type="button" className="button" onClick={() => setAdding(true)} disabled={rows.length >= 12}>Add marker</button>}
        {!sameMarkers(rows, DEFAULT_OOC_MARKERS) && <button type="button" className="text-button" onClick={() => change(DEFAULT_OOC_MARKERS.map((row) => ({ ...row, pair: !!row.close })))}>Reset to defaults</button>}
      </div>
    </fieldset>
  )
}

function MarkerRowEditor({ row, problem, only, onChange, onRemove }: { row: MarkerRow; problem: string | null; only: boolean; onChange: (part: Partial<MarkerRow>) => void; onRemove: () => void }) {
  const box = (value: string, label: string, set: (text: string) => void) =>
    <input value={value} maxLength={12} size={6} aria-label={label} aria-invalid={!!problem} onChange={(event) => set(event.target.value)} />
  return (
    <div>
      <div className="form-actions">
        {row.pair
          ? <span>Between {box(row.open, 'Opening marker', (open) => onChange({ open }))} and {box(row.close, 'Closing marker', (close) => onChange({ close }))}</span>
          : <span>Starts with {box(row.open, 'Starting word', (open) => onChange({ open }))}</span>}
        <button type="button" className="icon-button marker-remove" aria-label="Remove this marker" disabled={only} onClick={onRemove}><X aria-hidden="true" /></button>
      </div>
      {problem && <p className="subtle" role="alert">{problem}</p>}
    </div>
  )
}
