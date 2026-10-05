import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ImagePlus, RefreshCw, X } from 'lucide-react'
import { api } from '../../api'
import type { FeedPost, ImageJob } from '../../types'
import { imageAlt, imageFile, imageLine, isActive, provenance } from './imageState'

type Run = (action: () => Promise<unknown>) => Promise<void>
const RETRYABLE = ['failed', 'interrupted', 'cancelled']

/** The post's illustration and its controls (F3, F4). The text above never waits for it. */
export function PostImage({ post, onChange }: { post: FeedPost; onChange: () => void }) {
  const client = useQueryClient()
  const [details, setDetails] = useState(false)
  const [localOnly, setLocalOnly] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { image } = post
  const jobsKey = ['image-jobs', post.id]
  const jobs = useQuery({
    queryKey: [...jobsKey, image.job_id, image.status],
    queryFn: () => api<{ jobs: ImageJob[] }>(`/images/jobs?post_id=${encodeURIComponent(post.id)}`),
    enabled: details || image.status === 'queued',
  })
  const run: Run = async (action) => {
    try {
      await action()
      setError(null)
      onChange()
      await client.invalidateQueries({ queryKey: jobsKey })
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'That did not work.') }
  }
  const waiting = jobs.data?.jobs.find((job) => job.id === image.job_id)?.waiting_for
  return (
    <div className="post-image">
      <ImageView post={post} waiting={waiting} error={error} />
      <ImageActions post={post} details={details} setDetails={setDetails} run={run} generate={() => run(() => api('/images/jobs', { post_id: post.id, marked_nsfw: localOnly }))} />
      {details && <ImageDetails jobs={jobs.data?.jobs ?? []} localOnly={localOnly} setLocalOnly={setLocalOnly} run={run} />}
    </div>
  )
}

function ImageView({ post, waiting, error }: { post: FeedPost; waiting?: string | null; error: string | null }) {
  const { image } = post
  const line = imageLine(image, waiting)
  return <>
    {image.ref && <img src={imageFile(image.ref)} alt={imageAlt(image, post.events[0]?.summary ?? 'this moment')} loading="lazy" />}
    {line && <p className={image.status === 'failed' ? 'image-line error-text' : 'image-line subtle'} role="status">{line}</p>}
    {error && <p className="image-line error-text" role="alert">{error}</p>}
  </>
}

function ImageActions({ post, details, setDetails, run, generate }: { post: FeedPost; details: boolean; setDetails: (open: boolean) => void; run: Run; generate: () => Promise<void> }) {
  const { image } = post
  const jobPath = `/images/jobs/${image.job_id}`
  if (isActive(image.status)) {
    return <div className="post-actions"><button type="button" className="text-button" onClick={() => void run(() => api(`${jobPath}/cancel`, {}))}><X aria-hidden="true" />Cancel image</button></div>
  }
  return (
    <div className="post-actions">
      <button type="button" className="text-button" onClick={() => void generate()}>{image.ref ? <RefreshCw aria-hidden="true" /> : <ImagePlus aria-hidden="true" />}{image.ref ? 'New version' : 'Make an image'}</button>
      {RETRYABLE.includes(image.status) && <button type="button" className="text-button" onClick={() => void run(() => api(`${jobPath}/retry`, {}))}>Retry</button>}
      {image.status !== 'none' && <button type="button" className="text-button" aria-expanded={details} onClick={() => setDetails(!details)}>Image details</button>}
    </div>
  )
}

function ImageDetails({ jobs, localOnly, setLocalOnly, run }: { jobs: ImageJob[]; localOnly: boolean; setLocalOnly: (value: boolean) => void; run: Run }) {
  const versions = jobs.filter((job) => job.status === 'completed' && job.has_image)
  return (
    <div className="image-details">
      <label className="inline-check"><input type="checkbox" checked={localOnly} onChange={(event) => setLocalOnly(event.target.checked)} /> Treat the next image as NSFW (local backend only)</label>
      {versions.length > 1 && (
        <div className="image-versions" role="group" aria-label="Versions">
          {versions.map((job, index) => (
            <button key={job.id} type="button" className="image-version" aria-pressed={job.current} onClick={() => !job.current && void run(() => api(`/images/jobs/${job.id}/select`, {}))}>
              <img src={imageFile(job.id)} alt={`Version ${versions.length - index}`} loading="lazy" />
            </button>
          ))}
        </div>
      )}
      {jobs.map((job) => (
        <details key={job.id} open={job.current}>
          <summary>{new Date(job.created_at).toLocaleString()} · {job.status}{job.current ? ' · shown' : ''}</summary>
          <dl className="image-provenance">
            {provenance(job).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
            <div><dt>Prompt</dt><dd>{job.prompt}</dd></div>
            {job.error && <div><dt>Problem</dt><dd>{job.error}</dd></div>}
          </dl>
          {[...RETRYABLE, 'completed'].includes(job.status) && (
            <div className="form-actions">
              {job.retry_original_available && <button type="button" className="button" onClick={() => void run(() => api(`/images/jobs/${job.id}/retry`, {}))}>Retry this request</button>}
              <button type="button" className="button" onClick={() => void run(() => api(`/images/jobs/${job.id}/retry`, { current_settings: true }))}>Retry with current settings</button>
            </div>
          )}
        </details>
      ))}
      <p className="subtle">An image is an illustration of this moment. What it shows never changes what happened.</p>
    </div>
  )
}
