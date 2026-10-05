import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { api, upload } from '../../api'
import type { Generation, GenerationDraft, GeneratedImage, ImageBackend, PlannedShot, Shot, ShotAspect } from '../../types'
import { Notice } from '../../components/Feedback'
import { Field, TextArea, TextInput, Toggle } from '../../components/Fields'
import { composePrompt, generationLine, routeLine } from './loraState'
import { hashPicture, pngCopy } from './browserImage'
import { REFERENCES_KEY } from './queries'

const GENERATIONS_KEY = ['lora-generations']
const ASPECTS: ShotAspect[] = ['portrait', 'square', 'landscape']
const failure = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback
const newSeed = () => Math.floor(Math.random() * (2 ** 31 - 2)) + 1

/** Generate candidate pictures from an editable shot list. Nothing joins the set until kept. */
export function GeneratePictures() {
  const [open, setOpen] = useState(false)
  const generations = useQuery({
    queryKey: GENERATIONS_KEY, queryFn: () => api<{ generations: Generation[] }>('/lora/generations'),
    refetchInterval: (query) => query.state.data?.generations.some((item) => item.status === 'running') ? 2000 : false,
  })
  const list = generations.data?.generations ?? []
  return (
    <section className="form-stack lora-panel">
      <div className="backend-title"><h3>Generate pictures</h3></div>
      <p className="subtle">Draft a shot list from the appearance description and make candidates with your image backends. Every shot shares one description and one seed so the set stays consistent. Each request is checked like any image: NSFW goes only to a backend on this computer, and anything prohibited is refused. Nothing joins the set until you keep it.</p>
      {open ? <Planner close={() => setOpen(false)} running={list.some((item) => item.status === 'running')} />
        : <div className="form-actions"><button type="button" className="button" onClick={() => setOpen(true)}>Plan pictures</button></div>}
      {list.map((item) => <GenerationView key={item.id} generation={item} />)}
    </section>
  )
}

function usePlanPreview(body: Record<string, unknown> | null) {
  const [settled, setSettled] = useState(body)
  const key = JSON.stringify(body)
  useEffect(() => {
    const timer = setTimeout(() => setSettled(body), 400)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `key` stands for `body`.
  }, [key])
  return useQuery({
    queryKey: ['lora-generation-preview', JSON.stringify(settled)], enabled: settled !== null,
    queryFn: () => api<{ shots: PlannedShot[] }>('/lora/generations/preview', settled),
  })
}

type Plan = { base: string; seed: string; shots: Shot[] }

/** The editable plan, starting from the server's draft until the user changes something. */
function usePlan(draft: GenerationDraft | undefined) {
  const [base, setBase] = useState<string | null>(null)
  const [seed, setSeed] = useState<string | null>(null)
  const [shots, setShots] = useState<Shot[] | null>(null)
  const plan: Plan = { base: base ?? draft?.base ?? '', seed: seed ?? String(draft?.seed ?? ''), shots: shots ?? draft?.shots ?? [] }
  const reset = () => { setBase(null); setShots(null) }
  return { plan, setBase, setSeed, setShots, reset }
}

function isValid(plan: Plan) {
  return plan.base.trim() !== '' && plan.shots.length > 0 && plan.shots.every((shot) => shot.label.trim() && shot.shot.trim())
}

function useEnabledBackends(): ImageBackend[] {
  const backends = useQuery({ queryKey: ['image-backends'], queryFn: () => api<{ backends: ImageBackend[] }>('/images/backends') })
  return (backends.data?.backends ?? []).filter((backend) => backend.enabled && !backend.blocked_reason)
}

function Planner({ close, running }: { close: () => void; running: boolean }) {
  const draft = useQuery({ queryKey: ['lora-generation-draft'], queryFn: () => api<GenerationDraft>('/lora/generations/draft'), staleTime: Infinity })
  if (draft.data) return <PlanEditor draft={draft.data} close={close} running={running} />
  return draft.error ? <Notice tone="error">{failure(draft.error, 'The shot list could not be drafted.')}</Notice> : null
}

function PlanEditor({ draft, close, running }: { draft: GenerationDraft; close: () => void; running: boolean }) {
  const client = useQueryClient()
  const enabled = useEnabledBackends()
  const { plan, setBase, setSeed, setShots, reset } = usePlan(draft)
  const [backendId, setBackendId] = useState('')
  const [nsfw, setNsfw] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const body = isValid(plan) ? { base: plan.base, shots: plan.shots, marked_nsfw: nsfw, backend_id: backendId || null } : null
  const preview = usePlanPreview(body)
  const planned = body ? preview.data?.shots : undefined
  const generate = async () => {
    try {
      await api('/lora/generations', { ...body, seed: Number(plan.seed) })
      setError(null)
      await client.invalidateQueries({ queryKey: GENERATIONS_KEY })
    } catch (failed) { setError(failure(failed, 'The pictures were not started.')) }
  }
  return (
    <div className="form-stack">
      {enabled.length === 0 && <Notice tone="error">No image backend is enabled. Set one up in Settings, Images.</Notice>}
      <PlanSettings plan={plan} setBase={setBase} setSeed={setSeed} enabled={enabled} backendId={backendId} setBackendId={setBackendId} nsfw={nsfw} setNsfw={setNsfw} />
      <ShotList shots={plan.shots} setShots={setShots} reset={reset} planned={planned} promptFor={(shot) => composePrompt(draft.style, plan.base, shot.shot)} />
      {error && <Notice tone="error">{error}</Notice>}
      <div className="form-actions">
        <button type="button" className="button" onClick={close}>Close</button>
        <GenerateButton planned={planned} busy={running || preview.isFetching} running={running} generate={() => void generate()} />
      </div>
    </div>
  )
}

type SettingsProps = { plan: Plan; setBase: (value: string) => void; setSeed: (value: string) => void; enabled: ImageBackend[]; backendId: string; setBackendId: (value: string) => void; nsfw: boolean; setNsfw: (value: boolean) => void }

function PlanSettings({ plan, setBase, setSeed, enabled, backendId, setBackendId, nsfw, setNsfw }: SettingsProps) {
  return (
    <>
      <TextArea label="Description every shot starts from" value={plan.base} rows={3} maxLength={1500} onChange={setBase} hint="Drafted from the appearance description. Keep it the same across a set." />
      <div className="form-grid">
        <TextInput label="Seed" type="number" value={plan.seed} onChange={setSeed} hint="Shared by every shot. Codex and image APIs may ignore it." />
        <Field label="Backend">{(id) => (
          <select id={id} value={backendId} onChange={(event) => setBackendId(event.target.value)}>
            <option value="">Automatic, in your order</option>
            {enabled.map((backend) => <option key={backend.id} value={backend.id}>{backend.label}</option>)}
          </select>
        )}</Field>
      </div>
      <div className="form-actions"><button type="button" className="text-button" onClick={() => setSeed(String(newSeed()))}>New seed</button></div>
      <Toggle label="Treat these as NSFW (local backends only)" checked={nsfw} onChange={setNsfw} />
    </>
  )
}

function GenerateButton({ planned, busy, running, generate }: { planned?: PlannedShot[]; busy: boolean; running: boolean; generate: () => void }) {
  const sendable = planned?.filter((shot) => shot.backend).length ?? 0
  return (
    <button type="button" className="button primary" disabled={!planned || sendable === 0 || busy} onClick={generate}>
      {running ? 'Pictures are being made' : `Generate ${sendable} picture${sendable === 1 ? '' : 's'}`}
    </button>
  )
}

type ShotListProps = { shots: Shot[]; setShots: (shots: Shot[]) => void; reset: () => void; planned?: PlannedShot[]; promptFor: (shot: Shot) => string }

function ShotList({ shots, setShots, reset, planned, promptFor }: ShotListProps) {
  const edit = (index: number, change: Partial<Shot>) => setShots(shots.map((shot, at) => at === index ? { ...shot, ...change } : shot))
  return (
    <>
      <ol className="shot-list">{shots.map((shot, index) => (
        <ShotRow key={`${shot.key}-${index}`} shot={shot} prompt={planned?.[index]?.prompt ?? promptFor(shot)} planned={planned?.[index]}
          edit={(change) => edit(index, change)} remove={() => setShots(shots.filter((_shot, at) => at !== index))} />
      ))}</ol>
      <div className="form-actions">
        <button type="button" className="text-button" disabled={shots.length >= 40} onClick={() => setShots([...shots, { key: `custom-${Date.now()}`, label: 'New shot', shot: '', aspect: 'portrait' }])}><Plus aria-hidden="true" />Add a shot</button>
        <button type="button" className="text-button" onClick={reset}>Start over from the description</button>
      </div>
    </>
  )
}

function ShotRow({ shot, prompt, planned, edit, remove }: { shot: Shot; prompt: string; planned?: PlannedShot; edit: (change: Partial<Shot>) => void; remove: () => void }) {
  return (
    <li className="shot-row">
      <div className="form-grid">
        <TextInput label="Shot" value={shot.label} maxLength={80} onChange={(label) => edit({ label })} />
        <Field label="Shape">{(id) => (
          <select id={id} value={shot.aspect} onChange={(event) => edit({ aspect: event.target.value as ShotAspect })}>
            {ASPECTS.map((aspect) => <option key={aspect} value={aspect}>{aspect}</option>)}
          </select>
        )}</Field>
      </div>
      <TextArea label="What it shows" value={shot.shot} rows={2} maxLength={500} onChange={(text) => edit({ shot: text })} />
      <p className="subtle shot-prompt">Prompt sent: {prompt}</p>
      {planned && <p className={planned.backend ? 'subtle' : 'error-text'}>{routeLine(planned)}</p>}
      <button type="button" className="text-button danger-text" onClick={remove}><Trash2 aria-hidden="true" />Remove shot</button>
    </li>
  )
}

function GenerationView({ generation }: { generation: Generation }) {
  const client = useQueryClient()
  const refresh = () => client.invalidateQueries({ queryKey: GENERATIONS_KEY })
  return (
    <section className="form-stack">
      <div className="backend-title"><strong>Set from {new Date(generation.created_at).toLocaleString()}</strong><span className="badge">{generation.status}</span><span className="subtle">seed {generation.seed}</span></div>
      <p className="subtle" role="status">{generationLine(generation)}</p>
      {generation.status === 'running' && <div className="form-actions"><button type="button" className="text-button" onClick={() => void api(`/lora/generations/${generation.id}/cancel`, {}).then(refresh)}>Stop</button></div>}
      <ul className="reference-grid">{generation.images.map((image) => <GeneratedCard key={image.id} image={image} refresh={refresh} />)}</ul>
    </section>
  )
}

async function keepBody(id: string): Promise<{ body: Blob; hash?: string }> {
  const blob = await (await fetch(`/api/lora/generation-images/${id}/file`)).blob()
  if (blob.type !== 'image/webp') return { body: new Blob([]), hash: await hashPicture(blob) }
  const copy = await pngCopy(blob)
  return { body: copy, hash: await hashPicture(copy) }
}

function GeneratedCard({ image, refresh }: { image: GeneratedImage; refresh: () => Promise<unknown> }) {
  const client = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const act = async (action: () => Promise<unknown>) => {
    try { await action(); setError(null) } catch (failed) { setError(failure(failed, 'That did not work.')) }
    await refresh()
    await client.invalidateQueries({ queryKey: REFERENCES_KEY })
  }
  const keep = (role: 'train' | 'evaluation') => act(async () => {
    const { body, hash } = await keepBody(image.id)
    await upload(`/lora/generation-images/${image.id}/keep`, body, { role, ...(hash ? { dhash: hash } : {}) })
  })
  return (
    <li className="reference-card">
      <GeneratedPicture image={image} />
      {image.decision === 'kept' && <span className="badge">Kept in the set</span>}
      {image.status === 'completed' && image.decision === null && (
        <div className="post-actions">
          <button type="button" className="text-button" onClick={() => void keep('train')}>Keep for training</button>
          <button type="button" className="text-button" onClick={() => void keep('evaluation')}>Hold back</button>
          <button type="button" className="text-button danger-text" onClick={() => void act(() => api(`/lora/generation-images/${image.id}/discard`, {}))}>Discard</button>
        </div>
      )}
      {error && <p className="error-text">{error}</p>}
      <details><summary className="subtle">Prompt</summary><p className="subtle">{image.prompt}</p></details>
    </li>
  )
}

function made(image: GeneratedImage) {
  const parts = [image.backend_label, image.model, image.used_seed !== null ? `seed ${image.used_seed}` : null]
  return parts.filter(Boolean).join(' · ')
}

function GeneratedPicture({ image }: { image: GeneratedImage }) {
  const note = image.error ?? (image.decision === 'discarded' ? 'Discarded.' : image.status)
  return (
    <>
      {image.has_image ? <img src={`/api/lora/generation-images/${image.id}/file`} alt={`${image.label}, generated`} loading="lazy" />
        : <p className={image.status === 'failed' ? 'error-text' : 'subtle'}>{note}</p>}
      <strong className="reference-name">{image.label} {image.width && <small className="subtle">{image.width}×{image.height}</small>}</strong>
      {image.backend_label && <small className="subtle">{made(image)}</small>}
    </>
  )
}
