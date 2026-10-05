import { useState, type ChangeEvent } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Trash2 } from 'lucide-react'
import { api, upload } from '../../api'
import type { Crop, LoraReference, ReferenceRole, Rights } from '../../types'
import { Notice } from '../../components/Feedback'
import { Field, TextArea, TextInput } from '../../components/Fields'
import { RIGHTS, reviewLine } from './loraState'
import { cropCopy, hashPicture } from './browserImage'
import { REFERENCES_KEY, pictureUrl, useReferences } from './queries'

const failure = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback

function useSave() {
  const client = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const save = async (action: () => Promise<unknown>) => {
    try { await action(); setError(null) } catch (failed) { setError(failure(failed, 'That did not save.')) }
    await client.invalidateQueries({ queryKey: REFERENCES_KEY })
  }
  return { error, save }
}

/** Prepare: the user adds each picture and says where it came from and what it is for. */
export function Prepare() {
  const references = useReferences()
  const { error, save } = useSave()
  const [adding, setAdding] = useState<string | null>(null)
  const add = async (event: ChangeEvent<HTMLInputElement>) => {
    const chosen = [...(event.target.files ?? [])]
    event.target.value = ''
    const problems: string[] = []
    for (const [index, file] of chosen.entries()) {
      setAdding(`Adding ${index + 1} of ${chosen.length}`)
      const hash = await hashPicture(file)
      await upload('/lora/references', file, { name: file.name, ...(hash ? { dhash: hash } : {}) }).catch((failed) => problems.push(`${file.name}: ${failure(failed, 'not added')}`))
    }
    setAdding(null)
    await save(async () => { if (problems.length) throw new Error(problems.join(' ')) })
  }
  const list = references.data?.references ?? []
  return (
    <div className="form-stack">
      <p className="subtle">Add pictures of the character one by one. Nothing is collected from your folders. Use pictures you made, commissioned, generated or are licensed to use, and say where each came from. Community guides use 20 to 40, with a few full-body shots. Hold one or two back as evaluation references.</p>
      <Field label="Add pictures" hint="PNG or JPEG, up to 30 MB each. Exact copies are refused; near copies are flagged.">
        {(id, describedBy) => <input id={id} type="file" accept="image/png,image/jpeg" multiple aria-describedby={describedBy} disabled={adding !== null} onChange={(event) => void add(event)} />}
      </Field>
      {adding && <p className="subtle" role="status">{adding}</p>}
      {error && <Notice tone="error">{error}</Notice>}
      {references.data && <Notice>{reviewLine(references.data.review)}</Notice>}
      <ul className="reference-grid">{list.map((item) => <PrepareCard key={item.id} item={item} names={list} save={save} />)}</ul>
    </div>
  )
}

function PrepareCard({ item, names, save }: { item: LoraReference; names: LoraReference[]; save: (action: () => Promise<unknown>) => Promise<void> }) {
  const [note, setNote] = useState(item.source_note)
  const [reason, setReason] = useState(item.exclusion_reason)
  const put = (body: Record<string, unknown>) => save(() => api(`/lora/references/${item.id}`, body, 'PUT'))
  const similar = names.find((other) => other.id === item.similar_to)
  return (
    <li className="reference-card">
      <img src={pictureUrl(item.id)} alt={item.original_name || 'Reference picture'} loading="lazy" />
      <strong className="reference-name">{item.original_name || 'Picture'} <small className="subtle">{item.width}×{item.height}</small></strong>
      {item.missing && <p className="error-text">The file is missing from this workspace. Remove it and add it again.</p>}
      {similar && <p className="subtle">Looks nearly the same as {similar.original_name || 'another picture'}.</p>}
      <Field label="Where it came from">{(id) => (
        <select id={id} value={item.rights} onChange={(event) => void put({ rights: event.target.value as Rights })}>
          {RIGHTS.map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}
        </select>
      )}</Field>
      <TextInput label="Source note" value={note} maxLength={1000} onChange={setNote} placeholder="Artist, link or how it was made" />
      {note !== item.source_note && <button type="button" className="text-button" onClick={() => void put({ source_note: note })}>Save note</button>}
      <Field label="Use">{(id) => (
        <select id={id} value={item.role} onChange={(event) => void put(roleChange(event.target.value as ReferenceRole, reason))}>
          <option value="train">Training</option><option value="evaluation">Held out for evaluation</option><option value="excluded">Excluded</option>
        </select>
      )}</Field>
      {item.role === 'excluded' && <TextInput label="Why it is excluded" value={reason} maxLength={500} onChange={setReason} />}
      {item.role === 'excluded' && reason !== item.exclusion_reason && <button type="button" className="text-button" onClick={() => void put({ exclusion_reason: reason })}>Save reason</button>}
      <button type="button" className="text-button danger-text" onClick={() => void save(() => api(`/lora/references/${item.id}`, undefined, 'DELETE'))}><Trash2 aria-hidden="true" />Remove</button>
    </li>
  )
}

function roleChange(role: ReferenceRole, reason: string) {
  return role === 'excluded' ? { role, exclusion_reason: reason.trim() || 'Excluded by you' } : { role }
}

/** Review: captions and crops for the training pictures, and what still blocks training. */
export function Review() {
  const references = useReferences()
  const { error, save } = useSave()
  if (!references.data) return null
  const { review } = references.data
  const training = references.data.references.filter((item) => item.role === 'train')
  return (
    <div className="form-stack">
      <Notice tone={review.ready ? 'info' : 'error'}>{reviewLine(review)}</Notice>
      {review.blocking.length > 0 && <ul className="plain-list">{review.blocking.map((line) => <li key={line}>{line}</li>)}</ul>}
      {review.advice.length > 0 && <ul className="plain-list subtle">{review.advice.map((line) => <li key={line}>{line}</li>)}</ul>}
      <p className="subtle">Captions describe what changes between pictures (pose, clothes, setting) so the adapter learns the character, not the scene. [trigger] becomes your trigger word. Suggestions come from the appearance description, not from looking at the picture, and never replace what you wrote.</p>
      <div className="form-actions"><button type="button" className="button" onClick={() => void save(() => api('/lora/references/captions', {}))}>Suggest captions</button></div>
      {error && <Notice tone="error">{error}</Notice>}
      <ul className="reference-grid">{training.map((item) => <ReviewCard key={`${item.id}-${item.updated_at}`} item={item} save={save} />)}</ul>
    </div>
  )
}

function ReviewCard({ item, save }: { item: LoraReference; save: (action: () => Promise<unknown>) => Promise<void> }) {
  const [caption, setCaption] = useState(item.caption)
  const [cropping, setCropping] = useState(false)
  return (
    <li className="reference-card">
      <img src={pictureUrl(item.id, item.has_crop)} alt={item.original_name || 'Training picture'} loading="lazy" />
      <small className="subtle">{item.has_crop ? 'Cropped copy; the original is kept.' : 'Whole picture.'} {item.caption_origin === 'suggested' ? 'Caption suggested.' : ''}</small>
      <TextArea label="Caption" value={caption} rows={3} maxLength={2000} onChange={setCaption} />
      <div className="post-actions">
        {caption !== item.caption && <button type="button" className="text-button" onClick={() => void save(() => api(`/lora/references/${item.id}`, { caption }, 'PUT'))}>Save caption</button>}
        <button type="button" className="text-button" onClick={() => setCropping(!cropping)}>{cropping ? 'Close crop' : 'Crop'}</button>
        {item.has_crop && <button type="button" className="text-button" onClick={() => void save(() => api(`/lora/references/${item.id}/crop`, undefined, 'DELETE'))}>Use the whole picture</button>}
      </div>
      {cropping && <CropEditor item={item} save={save} done={() => setCropping(false)} />}
    </li>
  )
}

const FULL: Crop = { x: 0, y: 0, width: 1, height: 1 }

function CropEditor({ item, save, done }: { item: LoraReference; save: (action: () => Promise<unknown>) => Promise<void>; done: () => void }) {
  const [crop, setCrop] = useState<Crop>(item.crop ?? FULL)
  const slider = (key: keyof Crop, label: string) => (
    <label className="crop-slider">{label}
      <input type="range" min={key === 'width' || key === 'height' ? 5 : 0} max={100} value={Math.round(crop[key] * 100)}
        onChange={(event) => setCrop({ ...crop, [key]: Number(event.target.value) / 100 })} />
    </label>
  )
  const apply = () => save(async () => {
    const blob = await cropCopy(pictureUrl(item.id), crop, item.media_type)
    await upload(`/lora/references/${item.id}/crop`, blob, Object.fromEntries(Object.entries(fitted(crop)).map(([key, value]) => [key, String(value)])))
    done()
  })
  return (
    <div className="crop-editor">
      <div className="crop-preview">
        <img src={pictureUrl(item.id)} alt="" />
        <div className="crop-box" style={{ left: `${crop.x * 100}%`, top: `${crop.y * 100}%`, width: `${Math.min(crop.width, 1 - crop.x) * 100}%`, height: `${Math.min(crop.height, 1 - crop.y) * 100}%` }} />
      </div>
      {slider('x', 'Left')}{slider('y', 'Top')}{slider('width', 'Width')}{slider('height', 'Height')}
      <div className="form-actions"><button type="button" className="button" onClick={() => void apply()}>Save cropped copy</button></div>
    </div>
  )
}

function fitted(crop: Crop): Crop {
  return { ...crop, width: Math.max(0.05, Math.min(crop.width, 1 - crop.x)), height: Math.max(0.05, Math.min(crop.height, 1 - crop.y)) }
}
