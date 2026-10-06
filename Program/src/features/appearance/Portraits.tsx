import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, upload } from '../../api'
import { COMPANION_KEY, type View } from '../../companion'
import type { Companion, GeneratedImage, Generation, PlannedShot, PortraitDraft, Shot } from '../../types'
import { Notice } from '../../components/Feedback'
import { TextArea } from '../../components/Fields'
import { keepBody } from './browserImage'
import { routeLine } from './loraState'
import { PORTRAITS_KEY, cardNote, keepable, madeBy, redoLabel, redoable, sendsLine, setLine } from './portraitState'
import { REFERENCES_KEY } from './queries'

const failure = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback

/**
 * A profile picture, then a three-quarter view and a close-up, both made from the profile picture so all three
 * show the same person. Offered after creating a companion and from the Character page; always skippable.
 */
export function Portraits({ companion, go }: { companion: Companion; go: (view: View) => void }) {
  const name = companion.version.name
  const latest = useQuery({
    queryKey: PORTRAITS_KEY, queryFn: () => api<{ portraits: Generation | null }>('/lora/portraits').then((data) => data.portraits),
    refetchInterval: (query) => query.state.data?.status === 'running' ? 2000 : false,
  })
  const [planning, setPlanning] = useState(false)
  const set = latest.data
  const showPlanner = latest.isSuccess && (!set || planning)
  return (
    <section className="page">
      <header className="page-header">
        <div>
          <h1>Pictures of {name}</h1>
          <p className="subtle">A profile picture of {name} in everyday clothes, then a three-quarter view in another outfit and a close-up of their face, both made from it. The pictures you keep become {name}'s profile picture and join their reference pictures for the LoRA maker. You can skip this and come back from the Character page.</p>
        </div>
        <button type="button" className="button" onClick={() => go('conversation')}>{companion.portrait_reference_id ? 'Go to the chat' : 'Skip for now'}</button>
      </header>
      {latest.error && <Notice tone="error">{failure(latest.error, 'The pictures could not be loaded.')}</Notice>}
      {showPlanner && <Planner name={name} go={go} onStarted={() => setPlanning(false)} onCancel={set ? () => setPlanning(false) : undefined} />}
      {set && !planning && <PortraitSet set={set} name={name} go={go} onNew={() => setPlanning(true)} />}
    </section>
  )
}

function useDebounced<T>(value: T, delay = 400): T {
  const [settled, setSettled] = useState(value)
  const key = JSON.stringify(value)
  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delay)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `key` stands for `value`.
  }, [key, delay])
  return settled
}

interface PlannerProps { name: string; go: (view: View) => void; onStarted: () => void; onCancel?: () => void }

function Planner(props: PlannerProps) {
  const draft = useQuery({ queryKey: ['lora-portrait-draft'], queryFn: () => api<PortraitDraft>('/lora/portraits/draft'), staleTime: Infinity })
  if (draft.error) return <Notice tone="error">{failure(draft.error, 'The pictures could not be planned.')}</Notice>
  if (!draft.data) return null
  if (!draft.data.any_backend) {
    return <Notice action={<button type="button" className="text-button" onClick={() => props.go('settings/images')}>Open Settings</button>}>No image backend is set up yet. Add one in Settings, Images, then come back here from the Character page.</Notice>
  }
  return <PlanEditor draft={draft.data} {...props} />
}

function usePreview(body: Record<string, unknown> | null) {
  const settled = useDebounced(body)
  return useQuery({
    queryKey: ['lora-portrait-preview', JSON.stringify(settled)], enabled: settled !== null,
    queryFn: () => api<{ shots: PlannedShot[] }>('/lora/portraits/preview', settled),
  })
}

function PlanEditor({ draft, name, onStarted, onCancel }: PlannerProps & { draft: PortraitDraft }) {
  const client = useQueryClient()
  const [base, setBase] = useState(draft.base)
  const [shots, setShots] = useState<Shot[]>(draft.shots)
  const [withoutReference, setWithoutReference] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const body = { base, shots, without_reference: withoutReference }
  const preview = usePreview(base.trim() !== '' && shots.every((shot) => shot.shot.trim()) ? body : null)
  const planned = preview.data?.shots
  const start = async () => {
    setBusy(true)
    try {
      await api('/lora/portraits', { ...body, seed: draft.seed })
      setError(null)
      await client.invalidateQueries({ queryKey: PORTRAITS_KEY })
      onStarted()
    } catch (failed) { setError(failure(failed, 'The pictures were not started.')) } finally { setBusy(false) }
  }
  return (
    <div className="form-stack lora-panel">
      {!draft.reference_backend && <NoReference withoutReference={withoutReference} setWithoutReference={setWithoutReference} />}
      <TextArea label={`How ${name} looks`} value={base} rows={3} maxLength={1500} onChange={setBase} hint="From the appearance description. Every picture starts from it." />
      <ShotEditor shots={shots} setShots={setShots} planned={planned} />
      <PlanActions planned={planned} withoutReference={withoutReference} error={error} disabled={busy || preview.isFetching} onCancel={onCancel} start={() => void start()} />
    </div>
  )
}

interface ActionsProps { planned?: PlannedShot[]; withoutReference: boolean; error: string | null; disabled: boolean; onCancel?: () => void; start: () => void }

function PlanActions({ planned, withoutReference, error, disabled, onCancel, start }: ActionsProps) {
  return (<>
    {planned && <p className="subtle">{sendsLine(planned, withoutReference)}</p>}
    {error && <Notice tone="error">{error}</Notice>}
    <div className="form-actions">
      {onCancel && <button type="button" className="button" onClick={onCancel}>Back to the pictures</button>}
      <button type="button" className="button primary" disabled={!planned?.[0]?.backend || disabled} onClick={start}>Make the pictures</button>
    </div>
  </>)
}

function ShotEditor({ shots, setShots, planned }: { shots: Shot[]; setShots: (shots: Shot[]) => void; planned?: PlannedShot[] }) {
  return (
    <ol className="shot-list">{shots.map((shot, index) => (
      <li key={shot.key} className="shot-row">
        <TextArea label={`${index + 1}. ${shot.label}`} value={shot.shot} rows={2} maxLength={500} onChange={(text) => setShots(shots.map((item, at) => at === index ? { ...item, shot: text } : item))} />
        {planned?.[index] && <p className={planned[index].backend ? 'subtle' : 'error-text'}>{routeLine(planned[index])}</p>}
      </li>
    ))}</ol>
  )
}

function NoReference({ withoutReference, setWithoutReference }: { withoutReference: boolean; setWithoutReference: (value: boolean) => void }) {
  if (withoutReference) {
    return <Notice action={<button type="button" className="text-button" onClick={() => setWithoutReference(false)}>Undo</button>}>Making all three from the description alone. They may not look like the same person.</Notice>
  }
  return (
    <Notice action={<button type="button" className="text-button" onClick={() => setWithoutReference(true)}>Make them from the description instead</button>}>
      None of your image backends can make a picture from another picture, so pictures 2 and 3 would show a different person. Codex, OpenRouter, the OpenAI API, or a ComfyUI server with a reference workflow can.
    </Notice>
  )
}

function PortraitSet({ set, name, go, onNew }: { set: Generation; name: string; go: (view: View) => void; onNew: () => void }) {
  const client = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const [kept, setKept] = useState(false)
  const refresh = () => Promise.all([client.invalidateQueries({ queryKey: PORTRAITS_KEY }), client.invalidateQueries({ queryKey: REFERENCES_KEY }), client.invalidateQueries({ queryKey: COMPANION_KEY })])
  const act = async (action: () => Promise<unknown>) => {
    try { await action(); setError(null) } catch (failed) { setError(failure(failed, 'That did not work.')) }
    await refresh()
  }
  const running = set.status === 'running'
  const ready = keepable(set)
  return (
    <section className="form-stack" aria-labelledby="portrait-set-heading">
      <h2 id="portrait-set-heading" className="visually-hidden">The pictures</h2>
      <p className="subtle" role="status">{setLine(set)}</p>
      <ul className="reference-grid">{set.images.map((image) => (
        <PortraitCard key={image.id} image={image} images={set.images} canRedo={!running && redoable(image, set.images)}
          redo={() => void act(() => api(`/lora/portraits/${set.id}/redo?position=${image.position}`, {}))} />
      ))}</ul>
      {kept && <Notice action={<button type="button" className="text-button" onClick={() => go('conversation')}>Go to the chat</button>}>Saved. The profile picture now shows as {name}'s picture, and the pictures are in their reference set.</Notice>}
      {error && <Notice tone="error">{error}</Notice>}
      <div className="form-actions">
        {running && <button type="button" className="button" onClick={() => void act(() => api(`/lora/generations/${set.id}/cancel`, {}))}>Stop</button>}
        {!running && ready.length > 0 && <button type="button" className="button primary" onClick={() => void act(async () => { await keepAll(ready); setKept(true) })}>Keep {ready.length === set.images.length ? 'these' : `the ${ready.length} finished`}</button>}
        {!running && <button type="button" className="button" onClick={onNew}>Plan new pictures</button>}
      </div>
    </section>
  )
}

/** Keep each finished picture in the reference set; a kept profile picture (picture 1) becomes their picture. */
async function keepAll(ready: GeneratedImage[]) {
  for (const image of ready) {
    const { body, hash } = await keepBody(image.id)
    const after = await upload<Generation>(`/lora/generation-images/${image.id}/keep`, body, { role: 'train', ...(hash ? { dhash: hash } : {}) })
    const reference = after.images.find((item) => item.id === image.id)?.reference_id
    if (image.position === 0 && reference) await api('/lora/portrait', { reference_id: reference }, 'PUT')
  }
}

function PortraitCard({ image, images, canRedo, redo }: { image: GeneratedImage; images: GeneratedImage[]; canRedo: boolean; redo: () => void }) {
  const settled = image.status !== 'queued' && image.status !== 'running'
  return (
    <li className="reference-card">
      {image.has_image ? <img src={`/api/lora/generation-images/${image.id}/file`} alt={image.label} /> : <p className={image.status === 'failed' ? 'error-text' : 'subtle'}>{cardNote(image)}</p>}
      <strong className="reference-name">{image.position + 1}. {image.label}</strong>
      {image.backend_label && <small className="subtle">{madeBy(image)}</small>}
      {image.decision === 'kept' && <span className="badge">Kept</span>}
      {canRedo && settled && <button type="button" className="text-button" onClick={redo}>{redoLabel(image, images)}</button>}
    </li>
  )
}
