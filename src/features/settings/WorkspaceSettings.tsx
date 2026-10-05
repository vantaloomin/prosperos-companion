import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { SETTINGS_KEY, pcTimezone, useWorkspaceSettings } from '../../companion'
import { Pause, Play } from 'lucide-react'
import { api } from '../../api'
import type { WorkspaceSettings as Settings } from '../../types'
import { Notice } from '../../components/Feedback'
import { TextInput, Toggle } from '../../components/Fields'
import { timezones } from '../character/definition'

export function WorkspaceSettings() {
  const client = useQueryClient()
  const settings = useWorkspaceSettings()
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<Partial<Settings>>({})
  // Toggles show the new state at once and fall back to the saved state if the change is refused.
  const save = async (change: Partial<Settings> & { review_complete?: boolean }) => {
    setPending((current) => ({ ...current, ...change }))
    try {
      const saved = await api<Settings>('/settings', change, 'PUT')
      // Holding the saved state locally avoids a flicker before the shared cache re-renders.
      setPending(saved)
      client.setQueryData(SETTINGS_KEY, saved)
      setError(null)
      return true
    } catch (failure) {
      setPending({})
      setError(failure instanceof Error ? failure.message : 'That setting was not saved.')
      return false
    }
  }
  // The notice and its button go away; continue at the memory settings the review was about.
  const completeReview = async () => { if (await save({ review_complete: true })) document.getElementById('memory-heading')?.focus() }
  const pause = async (paused: boolean) => {
    try {
      const saved = await api<Settings>(paused ? '/pause' : '/resume', {})
      setPending(saved)
      client.setQueryData(SETTINGS_KEY, saved)
      void client.invalidateQueries({ queryKey: ['today'] })
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'That did not work.') }
  }
  if (!settings.data) return settings.isError ? <Notice tone="error">{settings.error.message}</Notice> : null
  const data = { ...settings.data, ...pending }
  return (
    <>
      {data.review_required && (
        <Notice action={<button type="button" className="text-button" onClick={() => void completeReview()}>Mark review complete</button>}>
          This workspace was restored from a backup. Look over its memories before turning on memory or background activity; a backup can hold things you asked to forget later.
        </Notice>
      )}
      {error && <Notice tone="error">{error}</Notice>}
      <section className="settings-section form-stack" aria-labelledby="activity-heading">
        <div>
          <h2 id="activity-heading">Pause</h2>
          <p className="subtle">{data.paused ? `Paused since ${new Date(data.paused_at!).toLocaleString()}. Nothing happens in your companion's life while paused, and resuming skips that time rather than filling it in.` : 'Pausing stops all background work and life events. You can still talk.'}</p>
        </div>
        <div className="form-actions">
          <button type="button" className="button" onClick={() => void pause(!data.paused)}>{data.paused ? <><Play aria-hidden="true" />Resume</> : <><Pause aria-hidden="true" />Pause</>}</button>
        </div>
      </section>
      <TimezoneSettings data={data} save={save} />
      <MemorySettings data={data} save={save} />
      <section className="settings-section form-stack" aria-labelledby="background-heading">
        <h2 id="background-heading">Background activity</h2>
        <Toggle label="Let their life continue while the app is open in the background" checked={data.background_activity} onChange={(value) => void save({ background_activity: value })}
          hint="Uses your model connection now and then while the Companion is running. Nothing runs while the app is closed." />
      </section>
    </>
  )
}

const ZONE_USE = 'Used for dates, quiet hours and what time it is for you.'
const ZONE_HINTS: Record<Settings['user_timezone_source'], string> = {
  pc: `Following this PC's timezone. ${ZONE_USE}`,
  chosen: `Set by you, so it stays put if this PC's timezone changes. ${ZONE_USE}`,
  default: ZONE_USE,
}

function TimezoneSettings({ data, save }: { data: Settings; save: (change: Partial<Settings>) => Promise<boolean> }) {
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

function MemorySettings({ data, save }: { data: Settings; save: (change: Partial<Settings>) => Promise<boolean> }) {
  return (
        <section className="settings-section form-stack" aria-labelledby="memory-heading">
          <h2 id="memory-heading" tabIndex={-1}>Memory</h2>
          <Toggle label="Remember things automatically" checked={data.automatic_memory} onChange={(value) => void save({ automatic_memory: value })}
            hint="When on, facts you state directly in new messages (your name, where you live, a plan with a date) are saved with the messages they came from, after each reply. Questions, hypotheticals, quotes and roleplay are never saved. Earlier messages are not scanned. When off, only what you choose to remember is saved; your conversation is kept either way." />
          <Toggle label="Allow sensitive memories" checked={data.sensitive_memory} onChange={(value) => void save({ sensitive_memory: value })}
            hint="Health, beliefs, money and similar details are only saved automatically with this on. Otherwise they wait in Memories as suggestions for you to keep or decline." />
          <Toggle label="Let the model suggest more" checked={data.model_memory_suggestions ?? false} disabled={!data.automatic_memory}
            onChange={(value) => void save({ model_memory_suggestions: value })}
            hint="Messages the built-in rules found nothing in are sent to your model connection in the background, which proposes facts in your own words. Nothing is kept until you choose Remember in Memories. Uses extra model time." />
          <Toggle label="Share what you've told them across alternate timelines" checked={data.share_profile_across_timelines} onChange={(value) => void save({ share_profile_across_timelines: value })}
            hint="Facts about you, your plans and how you're doing apply in every timeline, including ones you start with Edit from here. When off, each timeline only knows what you told it, plus what came before its edit. Shared moments and the companion's own life always stay in their own timeline." />
        </section>
  )
}
