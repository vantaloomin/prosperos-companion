import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Pencil, PlugZap, Trash2 } from 'lucide-react'
import { api } from '../../../api'
import { Notice } from '../../../components/Feedback'
import { useReturnFocus } from '../../../components/returnFocus'
import { ProfileEditor } from './ProfileEditor'
import { jobChoice } from './routing'
import type { ModelJob, ModelProfile, ModelsOverview } from './types'

const KEY = ['models']
type Result = { tone: 'info' | 'error'; text: string } | null
const failure = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback

/** Settings > Models (ported from Prospero's Study): profiles, then which profile does each job. */
export function ModelSettings() {
  const client = useQueryClient()
  const query = useQuery({ queryKey: KEY, queryFn: () => api<ModelsOverview>('/models') })
  const [editing, setEditing] = useState<string | 'new' | null>(null)
  const [result, setResult] = useState<Result>(null)
  const addButton = useReturnFocus<HTMLButtonElement>(editing === 'new')
  const refresh = (data?: ModelsOverview) => {
    if (data) client.setQueryData(KEY, data)
    void client.invalidateQueries({ queryKey: KEY })
    void client.invalidateQueries({ queryKey: ['connection'] })
  }
  if (!query.data) return null
  const { profiles, routes, jobs } = query.data
  const done = (saved?: ModelProfile) => { setEditing(null); if (saved) { setResult({ tone: 'info', text: `${saved.name} saved. New requests use it.` }); refresh() } }
  return <section className="settings-section form-stack" aria-labelledby="models-heading">
    <div>
      <h2 id="models-heading">Models</h2>
      <p className="subtle">A profile is one provider, model and key: hosted services, your Codex login, or a model running on this computer. The conversation profile does every job until you give a job its own. Saving never contacts the service.</p>
    </div>
    {profiles.length === 0 && editing !== 'new' && <p className="subtle">No model yet. Until you add one, your messages are saved and replies wait.</p>}
    {profiles.length > 0 && <ul className="model-profiles">
      {profiles.map(profile => editing === profile.id
        ? <li key={profile.id}><ProfileEditor profile={profile} onDone={done} /></li>
        : <ProfileCard key={profile.id} profile={profile} jobs={jobs.filter(job => routes[job.key] === profile.id)} onEdit={() => setEditing(profile.id)} onChanged={refresh} setResult={setResult} />)}
    </ul>}
    {editing === 'new' ? <ProfileEditor onDone={done} />
      : <div className="form-actions"><button ref={addButton} type="button" className="button" onClick={() => { setResult(null); setEditing('new') }}>Add a model profile</button></div>}
    {profiles.some(profile => profile.ready) && <JobAssignments overview={query.data} onChanged={refresh} setResult={setResult} />}
    {result && <Notice tone={result.tone}>{result.text}</Notice>}
  </section>
}

function ProfileCard({ profile, jobs, onEdit, onChanged, setResult }: { profile: ModelProfile; jobs: ModelJob[]; onEdit: () => void; onChanged: (data?: ModelsOverview) => void; setResult: (result: Result) => void }) {
  const [busy, setBusy] = useState(false)
  const [check, setCheck] = useState<{ count: number; note?: string } | null>(null)
  const run = async (work: () => Promise<void>) => { setBusy(true); try { await work() } catch (error) { setResult({ tone: 'error', text: failure(error, 'That did not work.') }) } finally { setBusy(false) } }
  const verify = () => run(async () => { setCheck(null); const found = await api<{ models: string[]; note?: string }>(`/models/profiles/${profile.id}/check`, {}); setCheck({ count: found.models.length, note: found.note }) })
  const remove = () => {
    if (!window.confirm(`Delete ${profile.name}? Its saved key is removed from your keychain${jobs.length ? ', and its jobs go back to the conversation profile' : ''}.`)) return
    void run(async () => { onChanged(await api<ModelsOverview>(`/models/profiles/${profile.id}`, undefined, 'DELETE')); setResult({ tone: 'info', text: `${profile.name} deleted.` }) })
  }
  const where = profile.config.provider === 'codex' ? 'Codex CLI login' : profile.config.base_url
  return <li className="model-profile">
    <div><span className="eyebrow">{profile.provider_name}</span><h3>{profile.name}</h3>
      <p className="subtle">{profile.config.model || 'Unfinished: choose a model'} · {where}{profile.has_saved_key ? ' · key saved' : ''}</p>
      {jobs.length > 0 && <p className="model-jobs"><Check size={14} aria-hidden="true" />{jobs.map(job => job.name).join(', ')}</p>}
      {check && <p className="subtle" role="status">Connected. {check.count ? `${check.count} models available. ` : ''}No text was generated.{check.note ? ` ${check.note}` : ''}</p>}
    </div>
    <div className="form-actions">
      <button type="button" className="button" onClick={() => void verify()} disabled={busy}><PlugZap size={15} aria-hidden="true" />{busy ? 'Checking…' : 'Check connection'}</button>
      <button type="button" className="button" onClick={onEdit} aria-label={`Edit ${profile.name}`}><Pencil size={15} aria-hidden="true" />Edit</button>
      <button type="button" className="button" onClick={remove} disabled={busy} aria-label={`Delete ${profile.name}`}><Trash2 size={15} aria-hidden="true" />Delete</button>
    </div>
  </li>
}

function JobAssignments({ overview, onChanged, setResult }: { overview: ModelsOverview; onChanged: (data?: ModelsOverview) => void; setResult: (result: Result) => void }) {
  const ready = overview.profiles.filter(profile => profile.ready)
  const change = async (job: ModelJob, profileId: string) => {
    try {
      onChanged(await api<ModelsOverview>('/models/routes', { job: job.key, profile_id: profileId || null }, 'PUT'))
      setResult({ tone: 'info', text: `${job.name} updated.` })
    } catch (error) { setResult({ tone: 'error', text: failure(error, 'Not changed.') }) }
  }
  return <fieldset className="model-routes form-stack"><legend>Which profile does each job</legend>
    {overview.jobs.map(job => {
      const choice = jobChoice(overview, job.key)
      const options = job.key === 'recall' ? ready.filter(profile => profile.config.embedding_model) : ready
      return <div className="field" key={job.key}>
        <label htmlFor={`model-job-${job.key}`}>{job.name}</label>
        <select id={`model-job-${job.key}`} value={choice.value} aria-describedby={`model-job-${job.key}-hint`} onChange={event => void change(job, event.target.value)}>
          <option value="">{job.key === 'chat' ? 'None' : `Same as conversation${choice.inherited ? ` (${choice.inherited})` : ''}`}</option>
          {options.map(profile => <option key={profile.id} value={profile.id}>{profile.name}</option>)}
        </select>
        <small id={`model-job-${job.key}-hint`}>{job.detail}</small>
      </div>
    })}
  </fieldset>
}
