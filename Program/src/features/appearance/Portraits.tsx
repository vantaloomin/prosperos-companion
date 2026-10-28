import { useEffect, useRef, useState, type ChangeEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ImagePlus } from 'lucide-react'
import { api, upload } from '../../api'
import { COMPANION_KEY, useCompanion, useWorkspaceSettings, type View } from '../../companion'
import type { Companion, GeneratedImage, Generation, PlannedShot, PortraitDraft, Shot } from '../../types'
import { Notice } from '../../components/Feedback'
import { TextArea } from '../../components/Fields'
import { keepBody, profileCopy } from './browserImage'
import { routeLine } from './loraState'
import { PORTRAITS_KEY, cardNote, keepable, redoLabel, redoable, sendsLine, setLine, sourceLine, startable } from './portraitState'
import { REFERENCES_KEY, pictureUrl } from './queries'

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
  const loraMaker = useWorkspaceSettings().data?.lora_maker
  return (
    <section className="page">
      <header className="page-header">
        <div>
          <h1>Pictures of {name}</h1>
          <p className="subtle">A profile picture of {name} in everyday clothes, then a three-quarter view in another outfit and a close-up of their face, both made from it. {keptLine(name, loraMaker)} You can also start from a picture of your own. You can skip this and come back from the Character page.</p>
        </div>
        <button type="button" className="button" onClick={() => go('conversation')}>{companion.portrait_reference_id ? 'Go to the chat' : 'Skip for now'}</button>
      </header>
      {latest.error && <Notice tone="error">{failure(latest.error, 'The pictures could not be loaded.')}</Notice>}
      {showPlanner && <Planner name={name} go={go} onStarted={() => setPlanning(false)} onCancel={set ? () => setPlanning(false) : undefined} />}
      {set && !planning && <PortraitSet set={set} name={name} go={go} onNew={() => setPlanning(true)} />}
    </section>
  )
}

/** The LoRA maker is named only while it is switched on. */
const keptLine = (name: string, loraMaker?: boolean) =>
  `The pictures you keep become ${name}'s profile picture${loraMaker ? ' and join their reference pictures for the LoRA maker' : ''}.`

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
    return <div className="form-stack lora-panel">
      <Notice action={<button type="button" className="text-button" onClick={() => props.go('settings/images')}>Open Settings</button>}>No image backend is set up yet. Add one in Settings, Images, then come back here from the Character page. You can still use a picture of your own as {props.name}'s profile picture.</Notice>
      <OwnPicture name={props.name} />
    </div>
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
  const [own, setOwn] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const body = { base, shots, without_reference: withoutReference && !own, own_picture: own }
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
      <FirstPicture name={name} own={own} setOwn={setOwn} />
      {!draft.reference_backend && <NoReference own={own} withoutReference={withoutReference} setWithoutReference={setWithoutReference} />}
      <TextArea label={`How ${name} looks`} value={base} rows={3} maxLength={1500} onChange={setBase} hint={own ? 'From the appearance description. Pictures 2 and 3 start from it, with your picture as the reference.' : 'From the appearance description. Every picture starts from it.'} />
      <ShotEditor shots={shots} setShots={setShots} planned={planned} own={own} />
      <PlanActions planned={planned} withoutReference={withoutReference && !own} error={error} disabled={busy || preview.isFetching} onCancel={onCancel} start={() => void start()} />
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
      <button type="button" className="button primary" disabled={!startable(planned) || disabled} onClick={start}>Make the pictures</button>
    </div>
  </>)
}

function ShotEditor({ shots, setShots, planned, own }: { shots: Shot[]; setShots: (shots: Shot[]) => void; planned?: PlannedShot[]; own: boolean }) {
  // With their own picture, picture 1 is shown above instead of planned here.
  return (
    <ol className="shot-list">{shots.map((shot, index) => own && index === 0 ? null : (
      <li key={shot.key} className="shot-row">
        <TextArea label={`${index + 1}. ${shot.label}`} value={shot.shot} rows={2} maxLength={500} onChange={(text) => setShots(shots.map((item, at) => at === index ? { ...item, shot: text } : item))}
          hint="Framing, pose, outfit and setting for this picture. How they look is added from above." />
        {planned?.[index] && <p className={planned[index].backend ? 'subtle' : 'error-text'}>{routeLine(planned[index])}</p>}
      </li>
    ))}</ol>
  )
}

function NoReference({ own, withoutReference, setWithoutReference }: { own: boolean; withoutReference: boolean; setWithoutReference: (value: boolean) => void }) {
  if (own) {
    return <Notice>None of your image backends can make a picture from another picture, so pictures 2 and 3 cannot be made from yours. Codex, OpenRouter, the OpenAI API, or a ComfyUI server with a reference workflow can. Your picture is still their profile picture.</Notice>
  }
  if (withoutReference) {
    return <Notice action={<button type="button" className="text-button" onClick={() => setWithoutReference(false)}>Undo</button>}>Making all three from the description alone. They may not look like the same person.</Notice>
  }
  return (
    <Notice action={<button type="button" className="text-button" onClick={() => setWithoutReference(true)}>Make them from the description instead</button>}>
      None of your image backends can make a picture from another picture, so pictures 2 and 3 would show a different person. Codex, OpenRouter, the OpenAI API, or a ComfyUI server with a reference workflow can.
    </Notice>
  )
}

/** Picture 1: made from the description, or a picture of the user's own. */
function FirstPicture({ name, own, setOwn }: { name: string; own: boolean; setOwn: (own: boolean) => void }) {
  return (
    <fieldset className="first-picture">
      <legend>Picture 1, the profile picture</legend>
      <label className="checkbox"><input type="radio" name="first-picture" checked={!own} onChange={() => setOwn(false)} /> Make it from the description</label>
      <label className="checkbox"><input type="radio" name="first-picture" checked={own} onChange={() => setOwn(true)} /> Use your own picture</label>
      {own && <OwnPicture name={name} />}
    </fieldset>
  )
}

/** The user's own picture: chosen here, it is their profile picture at once. */
function OwnPicture({ name }: { name: string }) {
  const client = useQueryClient()
  const current = useCompanion().data?.portrait_reference_id
  const input = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const choose = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setBusy(true)
    try {
      await upload('/lora/portrait/upload', await profileCopy(file), { name: file.name })
      setError(null)
    } catch (failed) { setError(failure(failed, 'This picture could not be used.')) } finally { setBusy(false) }
    await Promise.all([client.invalidateQueries({ queryKey: COMPANION_KEY }), client.invalidateQueries({ queryKey: REFERENCES_KEY }), client.invalidateQueries({ queryKey: ['lora-portrait-preview'] })])
  }
  return (
    <div className="own-picture">
      {current && <img src={pictureUrl(current)} alt={`${name}'s profile picture`} />}
      <div className="form-stack">
        {current && <p className="subtle">{name}'s profile picture now.</p>}
        <input ref={input} type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={(event) => void choose(event)} />
        <div>
          <button type="button" className="button" disabled={busy} aria-describedby="own-picture-types" onClick={() => input.current?.click()}>
            <ImagePlus aria-hidden="true" />{busy ? 'Adding the picture…' : current ? 'Choose another picture' : 'Choose a picture'}
          </button>
          <p className="subtle" id="own-picture-types">PNG, JPEG or WebP. It becomes {name}'s profile picture as soon as you pick it.</p>
        </div>
        <div aria-live="polite">{error && <Notice tone="error">{error}</Notice>}</div>
      </div>
    </div>
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
  // Finished pictures are kept as they are ready, picture 1 as the profile picture; Redo or a new set replaces them.
  const keeping = useRef(new Set<string>())
  useEffect(() => {
    const fresh = set.status === 'running' ? [] : keepable(set).filter((image) => !keeping.current.has(image.id))
    if (!fresh.length) return
    fresh.forEach((image) => keeping.current.add(image.id))
    keepAll(fresh).then(() => { setKept(true); setError(null) }, (failed) => setError(failure(failed, 'The pictures could not be kept.')))
      .finally(() => void Promise.all([client.invalidateQueries({ queryKey: PORTRAITS_KEY }), client.invalidateQueries({ queryKey: REFERENCES_KEY }), client.invalidateQueries({ queryKey: COMPANION_KEY })]))
  }, [set, client])
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
        {!running && error && ready.length > 0 && <button type="button" className="button primary" onClick={() => void act(async () => { await keepAll(ready); setKept(true) })}>Keep {ready.length === set.images.length ? 'these' : `the ${ready.length} finished`}</button>}
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
      {sourceLine(image) && <small className="subtle">{sourceLine(image)}</small>}
      {image.decision === 'kept' && <span className="badge">Kept</span>}
      {canRedo && settled && <button type="button" className="text-button" onClick={redo}>{redoLabel(image, images)}</button>}
    </li>
  )
}
