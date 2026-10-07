import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Pencil, PlugZap, Trash2 } from 'lucide-react'
import { api } from '../../../api'
import { Notice } from '../../../components/Feedback'
import { useReturnFocus } from '../../../components/returnFocus'
import { ProfileEditor } from './ProfileEditor'
import { jobChoice } from './routing'
import { isRecall, type ModelJob, type ModelProfile, type ModelsOverview } from './types'

const KEY = ['models']
type Result = { tone: 'info' | 'error'; text: string } | null
const failure = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback

type Editing = string | 'new' | 'new-recall' | null
interface Shared { overview: ModelsOverview; editing: Editing; setEditing: (value: Editing) => void; refresh: (data?: ModelsOverview) => void; result: Result; setResult: (result: Result) => void }

/** Settings > Models (ported from Prospero's Study): text profiles and which does each job, then recall profiles. */
export function ModelSettings() {
  const client = useQueryClient()
  const query = useQuery({ queryKey: KEY, queryFn: () => api<ModelsOverview>('/models') })
  const [editing, setEditing] = useState<Editing>(null)
  const [result, setResult] = useState<Result>(null)
  const refresh = (data?: ModelsOverview) => {
    if (data) client.setQueryData(KEY, data)
    void client.invalidateQueries({ queryKey: KEY })
    void client.invalidateQueries({ queryKey: ['connection'] })
  }
  if (!query.data) return null
  const shared: Shared = { overview: query.data, editing, setEditing, refresh, result, setResult }
  return <><TextProfiles {...shared} /><RecallProfiles {...shared} /></>
}

function TextProfiles({ overview, editing, setEditing, refresh, result, setResult }: Shared) {
  const addButton = useReturnFocus<HTMLButtonElement>(editing === 'new')
  const profiles = overview.profiles.filter(profile => !isRecall(profile.config))
  const done = finish(setEditing, setResult, refresh)
  return <section className="settings-section form-stack" aria-labelledby="models-heading">
    <div>
      <h2 id="models-heading">Models</h2>
      <p className="subtle">A profile is one provider, model and key: hosted services, your Codex login, or a model running on this computer. The conversation profile does every job until you give a job its own. Saving never contacts the service.</p>
    </div>
    {profiles.length === 0 && editing !== 'new' && <p className="subtle">No model yet. Until you add one, your messages are saved and replies wait.</p>}
    <ProfileList profiles={profiles} overview={overview} editing={editing} setEditing={setEditing} done={done} refresh={refresh} setResult={setResult} />
    {editing === 'new' ? <ProfileEditor onDone={done} />
      : <div className="form-actions"><button ref={addButton} type="button" className="button" onClick={() => { setResult(null); setEditing('new') }}>Add a model profile</button></div>}
    {profiles.some(profile => profile.ready) && <JobAssignments overview={overview} onChanged={refresh} setResult={setResult} />}
    {result && editing !== 'new-recall' && <Notice tone={result.tone}>{result.text}</Notice>}
  </section>
}

/** Recall gets its own profiles, so the service that finds memories is chosen apart from the one that writes. */
function RecallProfiles({ overview, editing, setEditing, refresh, setResult }: Shared) {
  const addButton = useReturnFocus<HTMLButtonElement>(editing === 'new-recall')
  const profiles = overview.profiles.filter(profile => isRecall(profile.config))
  const done = finish(setEditing, setResult, refresh)
  return <section className="settings-section form-stack" aria-labelledby="recall-profiles-heading">
    <div>
      <h2 id="recall-profiles-heading">Recall</h2>
      <p className="subtle">Semantic recall finds related memories even when the words differ, using an embedding model. It can use a different service from your text model: an embeddings model in Ollama or LM Studio, OpenAI, or an OpenAI-compatible service. Or let Built-in recall below run one on this PC. Without either, recall matches keywords only.</p>
    </div>
    <ProfileList profiles={profiles} overview={overview} editing={editing} setEditing={setEditing} done={done} refresh={refresh} setResult={setResult} />
    {editing === 'new-recall' ? <ProfileEditor recall onDone={done} />
      : <div className="form-actions"><button ref={addButton} type="button" className="button" onClick={() => { setResult(null); setEditing('new-recall') }}>Add a recall profile</button></div>}
    {profiles.length > 0 && <RecallChoice overview={overview} profiles={profiles} onChanged={refresh} setResult={setResult} />}
  </section>
}

function finish(setEditing: (value: Editing) => void, setResult: (result: Result) => void, refresh: () => void) {
  return (saved?: ModelProfile) => { setEditing(null); if (saved) { setResult({ tone: 'info', text: `${saved.name} saved. New requests use it.` }); refresh() } }
}

function ProfileList({ profiles, overview, editing, setEditing, done, refresh, setResult }: { profiles: ModelProfile[]; overview: ModelsOverview; editing: Editing; setEditing: (value: Editing) => void; done: (saved?: ModelProfile) => void; refresh: (data?: ModelsOverview) => void; setResult: (result: Result) => void }) {
  if (!profiles.length) return null
  return <ul className="model-profiles">
    {profiles.map(profile => editing === profile.id
      ? <li key={profile.id}><ProfileEditor profile={profile} onDone={done} /></li>
      : <ProfileCard key={profile.id} profile={profile} jobs={overview.jobs.filter(job => overview.routes[job.key] === profile.id)} onEdit={() => setEditing(profile.id)} onChanged={refresh} setResult={setResult} />)}
  </ul>
}

function RecallChoice({ overview, profiles, onChanged, setResult }: { overview: ModelsOverview; profiles: ModelProfile[]; onChanged: (data?: ModelsOverview) => void; setResult: (result: Result) => void }) {
  const change = async (profileId: string) => {
    try {
      onChanged(await api<ModelsOverview>('/models/routes', { job: 'recall', profile_id: profileId || null }, 'PUT'))
      setResult({ tone: 'info', text: 'Semantic recall updated.' })
    } catch (error) { setResult({ tone: 'error', text: failure(error, 'Not changed.') }) }
  }
  return <div className="field">
    <label htmlFor="model-job-recall">Which profile does recall</label>
    <select id="model-job-recall" value={overview.routes.recall ?? ''} aria-describedby="model-job-recall-hint" onChange={event => void change(event.target.value)}>
      <option value="">Keywords only</option>
      {profiles.filter(profile => profile.recall_ready).map(profile => <option key={profile.id} value={profile.id}>{profile.name}</option>)}
    </select>
    <small id="model-job-recall-hint">Built-in recall, when it is on, does recall instead.</small>
  </div>
}

function modelLine(profile: ModelProfile) {
  if (isRecall(profile.config)) return profile.config.embedding_model || 'Unfinished: choose an embedding model'
  return profile.config.model || 'Unfinished: choose a model'
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
      <p className="subtle">{modelLine(profile)} · {where}{profile.has_saved_key ? ' · key saved' : ''}</p>
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
    {overview.jobs.filter(job => job.key !== 'recall').map(job => {
      const choice = jobChoice(overview, job.key)
      const options = ready
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
