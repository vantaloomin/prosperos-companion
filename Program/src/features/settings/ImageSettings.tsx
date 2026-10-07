import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, RefreshCw, Trash2 } from 'lucide-react'
import { api } from '../../api'
import type { BackendCheck, BackendFiles, BackendKind, HostedProvider, ImageBackend, ImageSettings as Limits, ModelFiles, ModelLink, SamplerSettings, StyleLora } from '../../types'
import { Notice } from '../../components/Feedback'
import { useReturnFocus } from '../../components/returnFocus'
import { Field, TextArea, TextInput, Toggle } from '../../components/Fields'
import { BACKEND_KINDS, PROVIDERS, disclosureFor } from '../feed/imageState'
import { FILE_SLOTS, MAX_STYLE_LORAS, NEW_STYLE_LORA, NO_CHOICE, TURBO, fileChoices, filesBody, hasKrea, isChosen, isTuned, linksByRole, serverFiles, shownFiles, shownSampler, stylesBody, type FileSlot } from './modelFiles'

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
      <Toggle label="Send photos, selfies and memes in chat" checked={data.chat_photos} onChange={(value) => void save({ chat_photos: value })}
        hint="Ask what they're up to, or for a selfie or a meme, and they can answer with a picture. A photo of the moment is also that moment's feed picture. Made by the backends below under the same content rules." />
      <Toggle label="Let them send pictures without being asked" checked={data.unprompted_photos} disabled={!data.chat_photos} onChange={(value) => void save({ unprompted_photos: value })}
        hint="Now and then a reply comes with a photo or a meme, a few a day at most. If they may message you first (Life & cities), they sometimes text a photo of what they're out doing, once a day at most." />
      <Toggle label="If a backend fails, try the next one" checked={data.fallback} onChange={(value) => void save({ fallback: value })}
        hint="Only to a backend allowed to receive that request." />
      <div className="form-grid">
        <TextInput label="Most automatic images a day" type="number" value={limit ?? String(data.daily_limit)} hint="0 to 24." onChange={setLimit} />
        <Field label="Shape" hint="For post pictures and photos in chat. Memes are always square.">{(id, hint) => (
          <select id={id} aria-describedby={hint} value={data.aspect} onChange={(event) => void save({ aspect: event.target.value as Limits['aspect'] })}>
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
    if (busy) return false
    setBusy(true)
    try { await action(); await refresh(); setResult(null); return true } catch (error) { setResult({ tone: 'error', text: failure(error, 'That did not work.') }); return false } finally { setBusy(false) }
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
      <ComfyFiles backend={backend} put={(body) => act(() => api(`/images/backends/${backend.id}`, body, 'PUT'))} />
      {backend.kind === 'comfyui' && <ReferenceWorkflow backend={backend} save={(value) => act(() => api(`/images/backends/${backend.id}`, { reference_workflow: value }, 'PUT'))} />}
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

/** The built-in workflow's model, text encoder and VAE, picked from the files the ComfyUI server
 * lists. The server is only asked once this is opened; a server that cannot be asked takes typed names. */
function ModelFilePicker({ backend, saved, save }: { backend: ImageBackend; saved: ModelFiles; save: (files: ModelFiles) => Promise<boolean> }) {
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState<Partial<ModelFiles>>({})
  const [kreaOnly, setKreaOnly] = useState(true)
  const files = useBackendFiles(backend.id, open)
  const links = useQuery({ queryKey: ['image-model-links'], queryFn: () => api<{ links: ModelLink[] }>('/images/model-links'), enabled: open, staleTime: Infinity })
  const server = serverFiles(files.data, files.isError ? failure(files.error, 'The server could not be asked.') : null, saved)
  const shown = shownFiles(draft, saved, server.defaults)
  const store = async (body: ModelFiles) => { if (await save(body)) setDraft({}) }
  return (
    <details onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary className="subtle">Model files for the built-in workflow {isChosen(saved) ? '(your choice)' : '(defaults)'}</summary>
      <div className="form-stack">
        <p className="subtle">Pick the files your ComfyUI server has. The lists come from the server at this backend's address; nothing is downloaded or installed.</p>
        {open && !server.answered && <p className="subtle">Asking ComfyUI for its files…</p>}
        {server.error && <Notice tone="error">{server.error} Type the file names instead.</Notice>}
        {hasKrea(server.krea) && <Toggle label="Only Krea 2 files" checked={kreaOnly} onChange={setKreaOnly}
          hint="Files whose name or folder says Krea 2 (or the Qwen encoder and VAE it uses). Turn off to see every file." />}
        {server.answered && <div className="form-grid">
          {FILE_SLOTS.map((slot) => <FileField key={slot.key} slot={slot} options={server.options[slot.key]} krea={kreaOnly ? server.krea[slot.key] : []} value={shown[slot.key]} fallback={server.defaults[slot.key]} onChange={(value) => setDraft({ ...draft, [slot.key]: value })} />)}
        </div>}
        <FileActions changed={Object.keys(draft).length > 0} chosen={isChosen(saved)} busy={files.isFetching}
          save={() => void store(filesBody(shown, server.defaults))} cancel={() => setDraft({})} reset={() => void store(NO_CHOICE)} refresh={() => void files.refetch()} />
        <ModelLinks links={links.data?.links ?? []} />
      </div>
    </details>
  )
}

interface FileActionProps { changed: boolean; chosen: boolean; busy: boolean; save: () => void; cancel: () => void; reset: () => void; refresh: () => void }

function FileActions({ changed, chosen, busy, save, cancel, reset, refresh }: FileActionProps) {
  return <div className="form-actions">
    {changed && <>
      <button type="button" className="button primary" onClick={save}>Save files</button>
      <button type="button" className="button" onClick={cancel}>Cancel</button>
    </>}
    {chosen && <button type="button" className="text-button" onClick={reset}>Use the defaults</button>}
    {/* Marked busy, not disabled, so keyboard focus stays on it. */}
    <button type="button" className="text-button" aria-disabled={busy} onClick={() => { if (!busy) refresh() }}><RefreshCw aria-hidden="true" />Refresh list</button>
  </div>
}

/** A ComfyUI server's model files (built-in workflow only) and style LoRAs (any workflow). */
function ComfyFiles({ backend, put }: { backend: ImageBackend; put: (body: object) => Promise<boolean> }) {
  return <>
    {backend.model_files && !backend.custom_workflow && <ModelFilePicker backend={backend} saved={backend.model_files} save={put} />}
    {backend.sampler && !backend.custom_workflow && <SamplerPicker backend={backend} saved={backend.sampler} save={put} />}
    {backend.style_loras && <StyleLoraPicker backend={backend} saved={backend.style_loras} save={(rows) => put(stylesBody(rows))} />}
  </>
}

/** The built-in workflow's steps, CFG, sampler and scheduler, for a model that wants other settings
 * than Krea 2 Turbo's. The sampler and scheduler lists come from the server's KSampler. A custom
 * workflow keeps its own settings, so this is not shown for one. */
function SamplerPicker({ backend, saved, save }: { backend: ImageBackend; saved: SamplerSettings; save: (body: object) => Promise<boolean> }) {
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState<Partial<SamplerSettings>>({})
  const files = useBackendFiles(backend.id, open)
  const server = serverFiles(files.data, files.isError ? failure(files.error, 'The server could not be asked.') : null, NO_CHOICE)
  const defaults = files.data?.sampler_defaults ?? TURBO
  const shown = shownSampler(draft, saved, defaults)
  const store = async (body: object) => { if (await save(body)) setDraft({}) }
  const slot = (label: string, hint: string): FileSlot => ({ key: 'unet_name', label, role: null, hint })
  return (
    <details onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary className="subtle">Sampling {isTuned(saved) ? '(your settings)' : '(Krea 2 Turbo defaults)'}</summary>
      <div className="form-stack">
        <p className="subtle">Starts on Krea 2 Turbo's settings: {defaults.steps} steps, CFG {defaults.cfg}, {defaults.sampler_name} and {defaults.scheduler}. Change them when your model's page recommends others.</p>
        <div className="form-grid">
          <TextInput label="Steps" type="number" value={String(shown.steps)} hint="1 to 100. Turbo models need few." onChange={(value) => setDraft({ ...draft, steps: Number(value) })} />
          <TextInput label="CFG" type="number" value={String(shown.cfg)} hint="At 1 the negative prompt is ignored." onChange={(value) => setDraft({ ...draft, cfg: Number(value) })} />
          <FileField slot={slot('Sampler', 'From ComfyUI\'s KSampler.')} options={server.options.sampler_name} krea={[]} value={shown.sampler_name} fallback={defaults.sampler_name ?? ''} onChange={(value) => setDraft({ ...draft, sampler_name: value })} />
          <FileField slot={slot('Scheduler', 'From ComfyUI\'s KSampler.')} options={server.options.scheduler} krea={[]} value={shown.scheduler} fallback={defaults.scheduler ?? ''} onChange={(value) => setDraft({ ...draft, scheduler: value })} />
        </div>
        <FileActions changed={Object.keys(draft).length > 0} chosen={isTuned(saved)} busy={files.isFetching}
          save={() => void store(shown)} cancel={() => setDraft({})} reset={() => void store(defaults)} refresh={() => void files.refetch()} />
      </div>
    </details>
  )
}

/** The server's file lists, asked once the panel is opened and shared by the file and LoRA pickers. */
function useBackendFiles(id: string, open: boolean) {
  return useQuery({ queryKey: ['image-backend-files', id], queryFn: () => api<BackendFiles>(`/images/backends/${id}/files`), enabled: open, staleTime: Infinity, retry: false })
}

/** A dropdown of the server's files (only `krea` when given), or a text box when it listed none. */
function FileField({ slot, options, krea, value, fallback, onChange }: { slot: FileSlot; options: string[]; krea: string[]; value: string; fallback: string; onChange: (value: string) => void }) {
  const { label, hint, tip } = slot
  if (options.length === 0) return <TextInput label={label} value={value} maxLength={300} placeholder={fallback} hint={hint} tip={tip} onChange={onChange} />
  return <Field label={label} hint={hint} tip={tip}>{(id, describedBy) => (
    <select id={id} aria-describedby={describedBy} value={value} onChange={(event) => onChange(event.target.value)}>
      {fileChoices(options, value, krea, krea.length > 0).map(choice => <option key={choice.value} value={choice.value}>{choice.label}</option>)}
    </select>
  )}</Field>
}

/** Up to three LoRAs from the server's loras folder, applied after the character's own LoRA (which is
 * never offered here), each with a strength and the trigger words it needs. Any workflow takes them. */
function StyleLoraPicker({ backend, saved, save }: { backend: ImageBackend; saved: StyleLora[]; save: (rows: StyleLora[]) => Promise<boolean> }) {
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState<StyleLora[] | null>(null)
  const files = useBackendFiles(backend.id, open)
  const server = serverFiles(files.data, files.isError ? failure(files.error, 'The server could not be asked.') : null, NO_CHOICE)
  const store = async (body: StyleLora[]) => { if (await save(body)) setDraft(null) }
  return (
    <details onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary className="subtle">Style LoRAs {saved.length ? `(${saved.length})` : '(none)'}</summary>
      <div className="form-stack">
        <p className="subtle">Extra LoRAs for the look of every picture from this server, such as a phone-photo or realism LoRA. They apply after the character's own LoRA, when one is adopted, in this order.</p>
        {open && !server.answered && <p className="subtle">Asking ComfyUI for its LoRAs…</p>}
        {server.error && <Notice tone="error">{server.error} Type the file names instead.</Notice>}
        {server.answered && <StyleLoraRows rows={draft ?? saved} options={server.options.lora} krea={server.krea.lora} setRows={setDraft} />}
        {draft && <FileActions changed chosen={false} busy={files.isFetching} save={() => void store(draft)} cancel={() => setDraft(null)} reset={() => undefined} refresh={() => void files.refetch()} />}
      </div>
    </details>
  )
}

const LORA_SLOT: FileSlot = { key: 'unet_name', label: 'LoRA', role: null, hint: 'From ComfyUI\'s models/loras folder.' }

function StyleLoraRows({ rows, options, krea, setRows }: { rows: StyleLora[]; options: string[]; krea: string[]; setRows: (rows: StyleLora[]) => void }) {
  const [kreaOnly, setKreaOnly] = useState(true)
  const edit = (index: number, change: Partial<StyleLora>) => setRows(rows.map((row, at) => at === index ? { ...row, ...change } : row))
  return <>
    {krea.length > 0 && <Toggle label="Only Krea 2 LoRAs" checked={kreaOnly} onChange={setKreaOnly} hint="LoRAs whose name or folder says Krea 2. Turn off to see every LoRA." />}
    {rows.map((row, index) => <div key={index} className="form-grid">
      <FileField slot={{ ...LORA_SLOT, label: `LoRA ${index + 1}` }} options={options} krea={kreaOnly ? krea : []} value={row.name} fallback="" onChange={(name) => edit(index, { name })} />
      <TextInput label="Strength" type="number" value={String(row.strength)} hint="0.6 to 0.8 suits most style LoRAs." onChange={(value) => edit(index, { strength: Number(value) })} />
      <TextInput label="Trigger words" value={row.trigger} maxLength={200} hint="Put in front of the prompt when the LoRA needs them." onChange={(trigger) => edit(index, { trigger })} />
      <button type="button" className="text-button" onClick={() => setRows(rows.filter((_, at) => at !== index))}><Trash2 aria-hidden="true" />Remove</button>
    </div>)}
    {rows.length < MAX_STYLE_LORAS && <div className="form-actions">
      <button type="button" className="button" onClick={() => setRows([...rows, { ...NEW_STYLE_LORA, name: (kreaOnly && krea[0]) || options[0] || '' }])}>Add a LoRA</button>
    </div>}
  </>
}

/** Official pages for the built-in workflow's files. Pages only, never a direct download. */
function ModelLinks({ links }: { links: ModelLink[] }) {
  const groups = linksByRole(links)
  if (groups.length === 0) return null
  return <div>
    <p className="subtle"><strong>Where to get models.</strong> Put each file in the ComfyUI folder named, then refresh the list. Check the licence on each page before downloading.</p>
    <ul className="plain-list">
      {groups.flatMap(({ slot, links: items }) => items.map(link => <li key={link.name}>
        {slot.label}: <a className="text-button" href={link.url} target="_blank" rel="noreferrer">{link.name}</a>{link.file && <> · {link.file}</>}
        <br /><span className="subtle">{link.licence}</span>
      </li>))}
    </ul>
  </div>
}

/** ComfyUI makes a picture that follows another (the profile pictures) only with the user's own workflow for it. */
function ReferenceWorkflow({ backend, save }: { backend: ImageBackend; save: (value: string) => Promise<unknown> }) {
  const [text, setText] = useState('')
  return (
    <details>
      <summary className="subtle">Workflow for pictures made from a reference {backend.reference_workflow ? '(set)' : '(none)'}</summary>
      <div className="form-stack">
        <TextArea label="Reference workflow" value={text} rows={3} onChange={setText}
          hint="Used for the profile pictures, where pictures 2 and 3 are made from picture 1. ComfyUI's API format with {{prompt}} and {{reference_image}} as a LoadImage node's image, plus any of {{negative}}, {{seed}}, {{width}} and {{height}}. There is no built-in one." />
        <div className="form-actions">
          <button type="button" className="button" disabled={!text.trim()} onClick={() => void save(text.trim())}>Save workflow</button>
          {backend.reference_workflow && <button type="button" className="text-button danger-text" onClick={() => void save('')}>Remove it</button>}
        </div>
      </div>
    </details>
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
    <p className="subtle">{[where, backend.model, missingKey ? 'no API key' : '', backend.takes_reference ? 'can follow a reference picture' : ''].filter(Boolean).join(' · ')}</p>
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
          hint="Leave empty for the built-in Krea 2 Turbo workflow; its model files can be picked once the backend is added. A custom one is ComfyUI's API format with {{prompt}}, {{negative}}, {{seed}}, {{width}} and {{height}}." />
      </>}
      {kind === 'codex' && <TextInput label="Codex CLI location (optional)" value={cliPath} onChange={setCliPath} hint="Found on PATH when empty. Sign in once with codex login in a terminal; the app never sees your password or token." />}
      {kind === 'hosted' && <>
        <Field label="Provider" hint="The image service your API key is for.">{(id, hint) => (
          <select id={id} aria-describedby={hint} value={provider} onChange={(event) => { setProvider(event.target.value as HostedProvider); setAccepted(false) }}>
            {PROVIDERS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
          </select>
        )}</Field>
        <TextInput label="Image model" value={model} required onChange={setModel} placeholder={provider === 'openrouter' ? 'google/gemini-2.5-flash-image' : provider === 'google' ? 'imagen-4.0-generate-001' : 'gpt-image-1'}
          hint="The model's exact name from the provider's documentation." />
        <TextInput label="API key" type="password" value={apiKey} onChange={setApiKey} hint="Saved in your system's credential store." />
        {provider === 'other' && <TextInput label="API base URL" value={baseUrl} required onChange={setBaseUrl} hint="For an OpenAI-compatible image service, usually ending in /v1." />}
      </>}
      {disclosure && <Toggle label="I understand what it receives" checked={accepted} onChange={setAccepted} hint={disclosure} />}
      <div className="form-actions">
        <button type="submit" className="button primary" disabled={busy}>Add backend</button>
        <button type="button" className="button" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}
