import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { SETTINGS_KEY, useWorkspaceSettings } from '../../companion'
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
  const [zone, setZone] = useState<string | null>(null)
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
    } catch (failure) {
      setPending({})
      setError(failure instanceof Error ? failure.message : 'That setting was not saved.')
    }
  }
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
        <Notice action={<button type="button" className="text-button" onClick={() => void save({ review_complete: true })}>Mark review complete</button>}>
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
      <section className="settings-section form-stack" aria-labelledby="time-heading">
        <h2 id="time-heading">Your time</h2>
        <TextInput label="Your timezone" value={zone ?? data.user_timezone} onChange={setZone} list="settings-timezones" maxLength={64} hint="Used for dates and for what time it is for you." />
        <datalist id="settings-timezones">{timezones().map((item) => <option key={item} value={item} />)}</datalist>
        {zone !== null && zone !== data.user_timezone && <div className="form-actions"><button type="button" className="button primary" onClick={() => void save({ user_timezone: zone }).then(() => setZone(null))}>Save timezone</button></div>}
      </section>
      <section className="settings-section form-stack" aria-labelledby="memory-heading">
        <h2 id="memory-heading">Memory</h2>
        <Toggle label="Remember things automatically" checked={data.automatic_memory} onChange={(value) => void save({ automatic_memory: value })}
          hint="When on, facts you state directly can be saved as memories with the messages they came from. When off, only what you choose to remember is saved; your conversation is kept either way." />
        <Toggle label="Allow sensitive memories" checked={data.sensitive_memory} onChange={(value) => void save({ sensitive_memory: value })}
          hint="Health, relationships, money and similar details are only saved automatically with this on." />
        <Toggle label="Share what you've told them across alternate timelines" checked={data.share_profile_across_timelines} onChange={(value) => void save({ share_profile_across_timelines: value })}
          hint="Facts about you carry over if you start an alternate timeline. Fictional events always stay in their own timeline." />
      </section>
      <section className="settings-section form-stack" aria-labelledby="background-heading">
        <h2 id="background-heading">Background activity</h2>
        <Toggle label="Let their life continue while the app is open in the background" checked={data.background_activity} onChange={(value) => void save({ background_activity: value })}
          hint="Uses your model connection now and then while the Companion is running. Nothing runs while the app is closed." />
      </section>
    </>
  )
}
