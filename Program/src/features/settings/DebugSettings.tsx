import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { FastForward, Play, RotateCcw } from 'lucide-react'
import { api } from '../../api'
import { DEBUG_TIME_KEY, useDebugTime } from '../../appClock'
import { syncAppClock } from '../../appTime.ts'
import { useWorkspaceSettings } from '../../companion'
import type { DebugTime } from '../../types'
import { Notice } from '../../components/Feedback'
import { Field } from '../../components/Fields'
import { formatAppTime, SPEED_LABELS } from './debugText'

const JUMPS: { label: string; hours: number }[] = [
  { label: '1 hour', hours: 1 }, { label: '6 hours', hours: 6 }, { label: '1 day', hours: 24 },
  { label: '3 days', hours: 72 }, { label: '1 week', hours: 168 },
]

/** Calls to the debug time API; each answer is the new state, which the app clock follows at once. */
function useDebugCalls() {
  const client = useQueryClient()
  const [problem, setProblem] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const call = async (path: string, body: object = {}) => {
    setBusy(true)
    try {
      const saved = await api<DebugTime>(`/debug-time/${path}`, body)
      syncAppClock(saved)
      client.setQueryData(DEBUG_TIME_KEY, saved)
      setProblem(null)
      return saved
    } catch (error) {
      setProblem(error instanceof Error ? error.message : 'That did not work.')
      return null
    } finally { setBusy(false) }
  }
  const finish = async (keep: boolean) => {
    if (await call('finish', { keep })) void client.invalidateQueries({ predicate: (item) => item.queryKey[0] !== DEBUG_TIME_KEY[0] })
  }
  return { call, finish, busy, problem }
}

/** Settings > Debug: move the app's time ahead or run it faster, then go back (companion/debug_time.py). */
export function DebugSettings({ name }: { name: string }) {
  const status = useDebugTime()
  const { call, finish, busy, problem } = useDebugCalls()
  const data = status.data
  const who = name || 'your companion'
  const shown = problem ?? status.error?.message
  return (
    <section className="settings-section form-stack" aria-labelledby="debug-heading">
      <div>
        <h2 id="debug-heading">Debug time</h2>
        <p className="subtle">Move time ahead or make it run faster, to check several days of {who}'s life in a few minutes. Starting takes a backup first, and returning to real time undoes everything that happened in debug time unless you choose to keep it.</p>
      </div>
      {shown && <Notice tone="error">{shown}</Notice>}
      {data && (data.active ? <Controls data={data} who={who} busy={busy} call={call} finish={finish} /> : (
        <div className="form-actions">
          <button type="button" className="button" disabled={busy} onClick={() => void call('start')}><Play aria-hidden="true" />{busy ? 'Backing up…' : 'Start debug time'}</button>
        </div>
      ))}
    </section>
  )
}

interface ControlsProps {
  data: DebugTime; who: string; busy: boolean
  call: (path: string, body?: object) => Promise<DebugTime | null>; finish: (keep: boolean) => Promise<void>
}

function Controls({ data, who, busy, call, finish }: ControlsProps) {
  const workspace = useWorkspaceSettings()
  const zone = workspace.data?.user_timezone
  const background = workspace.data?.background_activity !== false
  const [target, setTarget] = useState('')
  return (
    <>
      <p>It is <strong>{formatAppTime(data.now, zone)}</strong> in the app. Real time is {formatAppTime(data.real_now, zone)}.</p>
      {!background && <Notice>Background activity is off (General), so {who} catches up as after a real absence: a few highlights when you look in. Turn it on to see every day fill in as it passes.</Notice>}
      {data.jumping ? (
        <div className="field">
          <label htmlFor="debug-progress">Living through to {formatAppTime(data.jumping.to, zone)}…</label>
          <progress id="debug-progress" value={data.jumping.done} max={1} />
        </div>
      ) : (
        <>
          <div className="field">
            <span className="field-label">Jump ahead</span>
            <div className="form-actions wrap">
              {JUMPS.map((jump) => (
                <button key={jump.hours} type="button" className="button" disabled={busy} onClick={() => void call('jump', { hours: jump.hours })}><FastForward aria-hidden="true" />{jump.label}</button>
              ))}
            </div>
          </div>
          <form className="form-actions wrap" onSubmit={(event) => { event.preventDefault(); if (target) void call('jump', { to: target }) }}>
            <Field label="Or go to a date and time" hint={`Your time${zone ? ` (${zone})` : ''}. Time only moves forward here.`}>
              {(id, describedBy) => <input id={id} type="datetime-local" value={target} aria-describedby={describedBy} onChange={(event) => setTarget(event.target.value)} />}
            </Field>
            <button type="submit" className="button" disabled={busy || !target}>Go</button>
          </form>
          <Field label="Speed" hint="Faster time also makes held replies and first messages arrive sooner.">
            {(id, describedBy) => (
              <select id={id} value={data.speed} aria-describedby={describedBy} disabled={busy} onChange={(event) => void call('speed', { speed: Number(event.target.value) })}>
                {data.speeds.map((speed) => <option key={speed} value={speed}>{SPEED_LABELS[speed] ?? `${speed}×`}</option>)}
              </select>
            )}
          </Field>
          <div className="form-actions wrap">
            <button type="button" className="button primary" disabled={busy} onClick={() => void finish(false)}><RotateCcw aria-hidden="true" />Return to real time</button>
            <button type="button" className="text-button" disabled={busy} onClick={() => void finish(true)}>Keep what happened and return</button>
          </div>
          <p className="subtle">Returning puts everything back as it was when you started. Keeping what happened leaves {who}'s life still until real time reaches where debug time got to. The backup {data.backup ? `"${data.backup}" ` : ''}stays in Backups either way.</p>
        </>
      )}
    </>
  )
}
