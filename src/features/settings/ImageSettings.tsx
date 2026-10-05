import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, Trash2 } from 'lucide-react'
import { api } from '../../api'
import type { BackendCheck, BackendKind, HostedProvider, ImageBackend, ImageSettings as Limits } from '../../types'
import { Notice } from '../../components/Feedback'
import { useReturnFocus } from '../../components/returnFocus'
import { Field, TextArea, TextInput, Toggle } from '../../components/Fields'
import { BACKEND_KINDS, PROVIDERS, disclosureFor } from '../feed/imageState'

const SETTINGS_KEY = ['image-settings']
const BACKENDS_KEY = ['image-backends']
type Result = { tone: 'info' | 'error'; text: string } | null
const failure = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback

/** Image backends and generation controls (PRD F3, F5–F9). Everything is off until set up here. */
export function ImageSettings() {
  const client = useQueryClient()
  const settings = useQuery({ queryKey: SETTINGS_KEY, queryFn: () => api<Limits>('/images/settings') })
  const backends = useQuery({ queryKey: BACKENDS_KEY, queryFn: () => api<{ backends: ImageBackend[] }>('/images/backends') })
  const [result, setResult] = useState<Result>(null)
  const [adding, setAdding] = useState(false)
  const addButton = useReturnFocus<HTMLButtonElement>(adding)
  const save = async (change: Partial<Limits>, done?: string) => {
    try {
      client.setQueryData(SETTINGS_KEY, await api<Limits>('/images/settings', change, 'PUT'))
      setResult(done ? { tone: 'info', text: done } : null)
      return true
    } catch (error) { setResult({ tone: 'error', text: failure(error, 'Not saved.') }); return false }
  }
  const refresh = () => client.invalidateQueries({ queryKey: BACKENDS_KEY })
  if (!settings.data || !backends.data) return null
  const data = settings.data
  const list = backends.data.backends
  const hasLocal = list.some((backend) => backend.enabled && backend.accepts_nsfw)
  return (
    <section className="settings-section form-stack" aria-labelledby="images-heading">
      <div>
        <h2 id="images-heading">Images</h2>
        <p className="subtle">Feed posts can have an illustration. Every request is checked on this computer first. NSFW requests only go to a ComfyUI server on this computer; Codex and image APIs only ever receive safe requests, and some things are never made anywhere.</p>
      </div>
      {list.length === 0 && <p className="subtle">No image backend is set up yet. Posts stay text-only until you add one.</p>}
      {list.length > 0 && !hasLocal && <p className="subtle">No local backend is enabled, so NSFW requests will be refused.</p>}
      <ol className="backend-list">
        {list.map((backend, index) => <BackendRow key={backend.id} backend={backend} index={index} count={list.length} refresh={refresh} setResult={setResult} />)}
      </ol>
      {adding ? <AddBackend onDone={() => { setAdding(false); void refresh() }} setResult={setResult} />
        : <div className="form-actions"><button ref={addButton} type="button" className="button" onClick={() => setAdding(true)}>Add an image backend</button></div>}
      <ImageControls data={data} save={save} />
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
    </section>
  )
}

function ImageControls({ data, save }: { data: Limits; save: (change: Partial<Limits>, done?: string) => Promise<boolean> }) {
  const [limit, setLimit] = useState<string | null>(null)
  const [style, setStyle] = useState<string | null>(null)
  const saveDrafts = async () => {
    if (await save({ ...(limit !== null ? { daily_limit: Number(limit) } : {}), ...(style !== null ? { style } : {}) }, 'Saved.')) { setLimit(null); setStyle(null) }
  }
  return <>
      <Toggle label="Make images for new posts automatically" checked={data.automatic_images} onChange={(value) => void save({ automatic_images: value })}
        hint="Needs background activity on. Only covers posts written from now on, never catch-up summaries, and stops at the daily limit." />
      <Toggle label="If a backend fails, try the next one" checked={data.fallback} onChange={(value) => void save({ fallback: value })}
        hint="Only to a backend allowed to receive that request." />
      <div className="form-grid">
        <TextInput label="Most automatic images a day" type="number" value={limit ?? String(data.daily_limit)} hint="0 to 24." onChange={setLimit} />
        <Field label="Shape">{(id) => (
          <select id={id} value={data.aspect} onChange={(event) => void save({ aspect: event.target.value as Limits['aspect'] })}>
            <option value="landscape">Landscape</option><option value="square">Square</option><option value="portrait">Portrait</option>
          </select>
        )}</Field>
      </div>
      <TextInput label="Style" value={style ?? data.style} maxLength={500} placeholder="Candid, natural-light photograph" hint="Starts every image prompt." onChange={setStyle} />
      {(limit !== null || style !== null) && (
        <div className="form-actions">
          <button type="button" className="button primary" onClick={() => void saveDrafts()}>Save</button>
          <button type="button" className="button" onClick={() => { setLimit(null); setStyle(null) }}>Cancel</button>
        </div>
      )}
  </>
}

function BackendRow({ backend, index, count, refresh, setResult }: { backend: ImageBackend; index: number; count: number; refresh: () => Promise<unknown>; setResult: (result: Result) => void }) {
  const [check, setCheck] = useState<BackendCheck | null>(null)
  const [busy, setBusy] = useState(false)
  // Busy controls are marked, not disabled: disabling the focused control would drop keyboard focus.
  const act = async (action: () => Promise<unknown>) => {
    if (busy) return
    setBusy(true)
    try { await action(); await refresh(); setResult(null) } catch (error) { setResult({ tone: 'error', text: failure(error, 'That did not work.') }) } finally { setBusy(false) }
  }
  const pending = Boolean(backend.disclosure && !backend.disclosure_accepted)
  return (
    <li className="backend-row">
      <BackendSummary backend={backend} />
      {backend.blocked_reason && (
        <Notice tone="error" action={<button type="button" className="button" aria-disabled={busy} onClick={() => void act(() => api(`/images/backends/${backend.id}/unblock`, {}))}>Signed in again</button>}>
          {backend.blocked_reason}
        </Notice>
      )}
      {pending && <p className="subtle">{backend.disclosure}</p>}
      <Toggle label="Enabled" checked={backend.enabled}
        onChange={(value) => void act(() => api(`/images/backends/${backend.id}`, { enabled: value, accept_disclosure: value && pending ? true : undefined }, 'PUT'))}
        hint={pending ? 'Turning it on accepts what it receives, described above.' : undefined} />
      {check && <Notice tone={check.ok ? 'info' : 'error'}>{check.summary}<ul>{check.details.map((line) => <li key={line}>{line}</li>)}</ul></Notice>}
      <div className="post-actions">
        <button type="button" className="text-button" aria-disabled={busy} onClick={() => void act(async () => setCheck(await api<BackendCheck>(`/images/backends/${backend.id}/check`, {})))}>Check</button>
        <button type="button" className="text-button" aria-disabled={busy} disabled={index === 0} aria-label={`Move ${backend.label} up`} onClick={() => void act(() => api(`/images/backends/${backend.id}/move`, { position: index - 1 }))}><ArrowUp aria-hidden="true" />Up</button>
        <button type="button" className="text-button" aria-disabled={busy} disabled={index === count - 1} aria-label={`Move ${backend.label} down`} onClick={() => void act(() => api(`/images/backends/${backend.id}/move`, { position: index + 1 }))}><ArrowDown aria-hidden="true" />Down</button>
        <button type="button" className="text-button danger-text" aria-disabled={busy} onClick={() => void act(() => api(`/images/backends/${backend.id}`, undefined, 'DELETE'))}><Trash2 aria-hidden="true" />Remove</button>
      </div>
    </li>
  )
}

function BackendSummary({ backend }: { backend: ImageBackend }) {
  const where = backend.kind === 'codex' ? 'Codex CLI' : backend.local ? 'This computer' : backend.base_url
  const missingKey = backend.kind === 'hosted' && !backend.has_key
  return <>
    <div className="backend-title">
      <strong>{backend.label}</strong>
      <span className="badge">{backend.accepts_nsfw ? 'Local · safe and NSFW' : 'Safe only'}</span>
      {backend.experimental && <span className="badge">Experimental</span>}
    </div>
    <p className="subtle">{[where, backend.model, missingKey ? 'no API key' : ''].filter(Boolean).join(' · ')}</p>
  </>
}

interface Draft { kind: BackendKind; provider: HostedProvider; baseUrl: string; model: string; apiKey: string; cliPath: string; workflow: string; controlled: boolean }

/** The request body for a new backend; only the fields its kind uses. */
function backendBody(draft: Draft, disclosure: string | null, accepted: boolean): Record<string, unknown> {
  const body: Record<string, unknown> = { kind: draft.kind, accept_disclosure: disclosure ? accepted : undefined, enabled: !disclosure || accepted }
  if (draft.kind === 'comfyui') return { ...body, base_url: draft.baseUrl, controlled_machine: draft.controlled, workflow: draft.workflow.trim() || undefined }
  if (draft.kind === 'codex') return { ...body, cli_path: draft.cliPath.trim() || undefined }
  return { ...body, provider: draft.provider, model: draft.model, api_key: draft.apiKey || undefined, base_url: draft.baseUrl.trim() || undefined }
}

function AddBackend({ onDone, setResult }: { onDone: () => void; setResult: (result: Result) => void }) {
  const [kind, setKind] = useState<BackendKind>('comfyui')
  const [provider, setProvider] = useState<HostedProvider>('openrouter')
  const [baseUrl, setBaseUrl] = useState('http://127.0.0.1:8188')
  const [model, setModel] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [cliPath, setCliPath] = useState('')
  const [workflow, setWorkflow] = useState('')
  const [controlled, setControlled] = useState(false)
  const [accepted, setAccepted] = useState(false)
  const [busy, setBusy] = useState(false)
  const disclosure = disclosureFor(kind, provider, baseUrl, controlled)
  const chooseKind = (next: BackendKind) => {
    setKind(next)
    setBaseUrl(next === 'comfyui' ? 'http://127.0.0.1:8188' : '')
    setAccepted(false)
  }
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    try {
      await api('/images/backends', backendBody({ kind, provider, baseUrl, model, apiKey, cliPath, workflow, controlled }, disclosure, accepted))
      const leftOff = disclosure && !accepted
      setResult({ tone: 'info', text: leftOff ? 'Added, but left off until you accept what it receives.' : 'Backend added. Use Check to confirm it can run.' })
      onDone()
    } catch (error) { setResult({ tone: 'error', text: failure(error, 'Not added.') }) } finally { setBusy(false) }
  }
  return (
    <form className="form-stack backend-form" onSubmit={submit}>
      <Field label="Kind" hint={BACKEND_KINDS.find((item) => item.id === kind)?.hint}>{(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} value={kind} autoFocus onChange={(event) => chooseKind(event.target.value as BackendKind)}>
          {BACKEND_KINDS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
        </select>
      )}</Field>
      {kind === 'comfyui' && <>
        <TextInput label="ComfyUI address" value={baseUrl} required onChange={setBaseUrl} hint="The app connects to this server only. It never starts or stops ComfyUI." />
        <Toggle label="This address is a machine I control" checked={controlled} onChange={setControlled} hint="Only for your own computer on your network. A rented or shared GPU service is not." />
        <TextArea label="Custom workflow (optional)" value={workflow} rows={3} onChange={setWorkflow}
          hint="Leave empty for the built-in Krea 2 Turbo workflow (unverified). A custom one is ComfyUI's API format with {{prompt}}, {{negative}}, {{seed}}, {{width}} and {{height}}." />
      </>}
      {kind === 'codex' && <TextInput label="Codex CLI location (optional)" value={cliPath} onChange={setCliPath} hint="Found on PATH when empty. Sign in once with codex login in a terminal; the app never sees your password or token." />}
      {kind === 'hosted' && <>
        <Field label="Provider">{(id) => (
          <select id={id} value={provider} onChange={(event) => { setProvider(event.target.value as HostedProvider); setAccepted(false) }}>
            {PROVIDERS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
          </select>
        )}</Field>
        <TextInput label="Image model" value={model} required onChange={setModel} placeholder={provider === 'openrouter' ? 'google/gemini-2.5-flash-image' : provider === 'google' ? 'imagen-4.0-generate-001' : 'gpt-image-1'} />
        <TextInput label="API key" type="password" value={apiKey} onChange={setApiKey} hint="Saved in your system's credential store." />
        {provider === 'other' && <TextInput label="API base URL" value={baseUrl} required onChange={setBaseUrl} />}
      </>}
      {disclosure && <Toggle label="I understand what it receives" checked={accepted} onChange={setAccepted} hint={disclosure} />}
      <div className="form-actions">
        <button type="submit" className="button primary" disabled={busy}>Add backend</button>
        <button type="button" className="button" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}
