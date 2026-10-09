import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { NotificationPreview, NotificationSettings as Values } from '../../types'
import { Notice } from '../../components/Feedback'
import { Field, TextInput, Toggle } from '../../components/Fields'
import { PresetSelect, Stepper } from '../../components/NumberFields'
import { countText, minutesText } from '../../components/numberBounds'
import { currentPermission, permissionNote } from '../notifications/permission'
import { usePhoneStatus } from '../phone/phoneAccess'
import { PhonePush } from './PhonePush'
import { SectionPending } from '../../components/SectionPending'

const KEY = ['notification-settings']
type Draft = Partial<Record<'quiet_start' | 'quiet_end', string>>

const PREVIEWS: { value: NotificationPreview; label: string }[] = [
  { value: 'name', label: 'Name only' },
  { value: 'full', label: 'Name and what happened' },
  { value: 'private', label: 'Nothing personal' },
]

/** Settings and prompts here stay neutral whatever the character's traits (PRD C6, M4). */
export function NotificationSettings() {
  const client = useQueryClient()
  const settings = useQuery({ queryKey: KEY, queryFn: () => api<Values>('/notifications/settings') })
  const [result, setResult] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const [permission, setPermission] = useState(currentPermission)
  const onPhone = !!usePhoneStatus().data?.remote
  const save = async (change: Partial<Values>, done?: string) => {
    try {
      client.setQueryData(KEY, await api<Values>('/notifications/settings', change, 'PUT'))
      setResult(done ? { tone: 'info', text: done } : null)
      return true
    } catch (error) {
      setResult({ tone: 'error', text: error instanceof Error ? error.message : 'Not saved.' })
      return false
    }
  }
  const toggle = async (value: boolean) => {
    if (!value) return void save({ enabled: false })
    let state = currentPermission()
    if (state === 'default') state = await Notification.requestPermission()
    setPermission(state)
    if (state === 'granted') await save({ enabled: true })
  }
  if (!settings.data) return <SectionPending queries={[settings]} heading="notifications-heading" title="Notifications" />
  const data = settings.data
  const note = permissionNote(permission)
  return (
    <section className="settings-section form-stack" aria-labelledby="notifications-heading">
      <div>
        <h2 id="notifications-heading">Notifications</h2>
        <p className="subtle">{onPhone
          ? 'Notifications for new posts and messages, with the same quiet hours and limits as on your PC. If several are waiting, you get one summary instead.'
          : 'Desktop notifications for new posts made while the app runs in the background. They are shown only while the Companion is open in a browser tab. If several are waiting, you get one summary instead. Paired phones can also get them while the app is closed.'}</p>
      </div>
      {onPhone ? <PhonePush enabled={data.enabled} onEnable={() => save({ enabled: true })} /> : <>
        <Toggle label="Show desktop notifications" checked={data.enabled} disabled={!data.enabled && (permission === 'denied' || permission === 'unsupported')} onChange={(value) => void toggle(value)}
          hint="Turning this off also cancels any that are waiting, on paired phones too." />
        {note && !data.enabled && <Notice tone="info">{note}</Notice>}
      </>}
      <Field label="What notifications show" hint="Choose Nothing personal if other people can see your screen or lock screen.">
        {(id, hint) => (
          <select id={id} aria-describedby={hint} value={data.preview} onChange={(event) => void save({ preview: event.target.value as NotificationPreview })}>
            {PREVIEWS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        )}
      </Field>
      <Limits data={data} save={save} />
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
    </section>
  )
}

function Limits({ data, save }: { data: Values; save: (change: Partial<Values>, done?: string) => Promise<boolean> }) {
  const [draft, setDraft] = useState<Draft>({})
  const changed = Object.entries(draft).filter(([key, value]) => value !== undefined && value !== String(data[key as keyof Draft]))
  const saveLimits = async () => {
    const change = Object.fromEntries(changed)
    if (await save(change, 'Notification settings saved.')) setDraft({})
  }
  return (
    <>
      <div className="form-grid">
        <TextInput label="Quiet hours start" type="time" value={draft.quiet_start ?? data.quiet_start} hint="Nothing is shown in quiet hours. Use the same start and end for none."
          onChange={(value) => setDraft((current) => ({ ...current, quiet_start: value }))} />
        <TextInput label="Quiet hours end" type="time" value={draft.quiet_end ?? data.quiet_end} hint="In your timezone. Quiet hours can run past midnight."
          onChange={(value) => setDraft((current) => ({ ...current, quiet_end: value }))} />
        <Stepper label="Most notifications a day" value={data.daily_cap} min={1} max={6} format={(value) => countText(value, 'notification', 'notifications')}
          onChange={(value) => void save({ daily_cap: value }, 'Saved.')} />
        <PresetSelect label="Time between notifications" value={data.min_gap_minutes} presets={[30, 60, 120, 180, 240, 360, 720]} format={minutesText}
          onChange={(value) => void save({ min_gap_minutes: value }, 'Saved.')} />
      </div>
      {changed.length > 0 && <div className="form-actions"><button type="button" className="button primary" onClick={() => void saveLimits()}>Save</button><button type="button" className="button" onClick={() => setDraft({})}>Cancel</button></div>}
    </>
  )
}
