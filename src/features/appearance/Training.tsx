import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { LoraSettings, RunOptions, TrainerDescription, TrainingRun } from '../../types'
import { Notice } from '../../components/Feedback'
import { Field, TextInput, Toggle } from '../../components/Fields'
import { TRIGGER_PATTERN, checkpointLine, progressLine } from './loraState'
import { ADAPTERS_KEY, RUNS_KEY, useReferences, useRuns } from './queries'

const TRAINER_KEY = ['lora-trainer']
const SETTINGS_KEY = ['lora-settings']
const failure = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback

/** Configure: the exact trainer and model, what they need and download, then the run's options. */
export function Configure({ onStarted }: { onStarted: () => void }) {
  const trainer = useQuery({ queryKey: TRAINER_KEY, queryFn: () => api<TrainerDescription>('/lora/trainer') })
  const settings = useQuery({ queryKey: SETTINGS_KEY, queryFn: () => api<LoraSettings>('/lora/settings') })
  if (!trainer.data || !settings.data) return null
  return (
    <div className="form-stack">
      <TrainerFacts trainer={trainer.data} />
      <TrainerSettings key={JSON.stringify(settings.data)} settings={settings.data} trainer={trainer.data} />
      <RunForm trainer={trainer.data} onStarted={onStarted} />
    </div>
  )
}

function TrainerFacts({ trainer }: { trainer: TrainerDescription }) {
  return (
    <section className="lora-panel">
      <div className="backend-title"><strong>{trainer.name}</strong><span className="badge">{trainer.verified ? 'Verified' : 'Not verified on hardware'}</span></div>
      <p className="subtle">Targets {trainer.tested}, model architecture {trainer.arch}, adapters as LoKr or LoRA .safetensors. The app runs your own install; it never installs the trainer or downloads models itself.</p>
      <ul className="plain-list subtle">{trainer.requirements.map((line) => <li key={line}>{line}</li>)}</ul>
      <p className="subtle">{trainer.control}</p>
    </section>
  )
}

function TrainerSettings({ settings, trainer }: { settings: LoraSettings; trainer: TrainerDescription }) {
  const client = useQueryClient()
  const [draft, setDraft] = useState(settings)
  const [result, setResult] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const set = (change: Partial<LoraSettings>) => setDraft({ ...draft, ...change })
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    try {
      await api('/lora/settings', draft, 'PUT')
      await client.invalidateQueries({ queryKey: SETTINGS_KEY })
      await client.invalidateQueries({ queryKey: TRAINER_KEY })
      setResult({ tone: 'info', text: 'Saved.' })
    } catch (error) { setResult({ tone: 'error', text: failure(error, 'Not saved.') }) }
  }
  return (
    <form className="form-stack lora-panel" onSubmit={submit}>
      <TextInput label="AI Toolkit's Python" value={draft.python_path} onChange={(python_path) => set({ python_path })} placeholder="C:\ai-toolkit\venv\Scripts\python.exe" hint="The interpreter of the virtual environment AI Toolkit was installed into." />
      <TextInput label="AI Toolkit folder" value={draft.trainer_dir} onChange={(trainer_dir) => set({ trainer_dir })} placeholder="C:\ai-toolkit" />
      <TextInput label="Base model" value={draft.base_model} onChange={(base_model) => set({ base_model })} hint={`Default ${trainer.default_base_model}. A local folder or .safetensors file avoids downloading it.`} />
      <TextInput label="ComfyUI loras folder (optional)" value={draft.comfy_lora_dir} onChange={(comfy_lora_dir) => set({ comfy_lora_dir })} placeholder="C:\ComfyUI\models\loras" hint="When set, adopting or evaluating an adapter copies it here so ComfyUI can load it." />
      {!trainer.check.ok && <Notice tone="error">{trainer.check.problems.join(' ')}</Notice>}
      {trainer.check.notes.map((line) => <Notice key={line}>{line}</Notice>)}
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
      <div className="form-actions"><button type="submit" className="button">Save trainer settings</button></div>
    </form>
  )
}

function RunForm({ trainer, onStarted }: { trainer: TrainerDescription; onStarted: () => void }) {
  const client = useQueryClient()
  const references = useReferences()
  const [name, setName] = useState('')
  const [trigger, setTrigger] = useState('')
  const [options, setOptions] = useState<RunOptions>(trainer.defaults)
  const [accepted, setAccepted] = useState(false)
  const [attested, setAttested] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const ready = references.data?.review.ready ?? false
  const valid = name.trim() && TRIGGER_PATTERN.test(trigger) && accepted && attested && trainer.check.ok && ready
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    try {
      await api('/lora/runs', { name, trigger, ...options, accept_disclosure: accepted, attest_fictional_adult: attested })
      await client.invalidateQueries({ queryKey: RUNS_KEY })
      onStarted()
    } catch (failed) { setError(failure(failed, 'Training did not start.')) }
  }
  return (
    <form className="form-stack lora-panel" onSubmit={submit}>
      <h3>New training run</h3>
      {!ready && <Notice tone="error">The pictures are not ready yet. Finish Prepare and Review first.</Notice>}
      <div className="form-grid">
        <TextInput label="Name" value={name} maxLength={80} onChange={setName} placeholder="Mira, autumn look" />
        <TextInput label="Trigger word" value={trigger} maxLength={40} onChange={setTrigger} placeholder="m1ra" hint="A made-up word, letters, numbers, - or _. Prompts use it to call up the character." />
      </div>
      <OptionFields options={options} setOptions={setOptions} />
      <Toggle label="I understand what training uses and downloads" checked={accepted} onChange={setAccepted} hint={trainer.disclosure} />
      <Toggle label="These pictures show a fictional adult character" checked={attested} onChange={setAttested} hint="Not a real person, and not anyone under 18." />
      {error && <Notice tone="error">{error}</Notice>}
      <div className="form-actions"><button type="submit" className="button primary" disabled={!valid}>Start training</button></div>
    </form>
  )
}

function OptionFields({ options, setOptions }: { options: RunOptions; setOptions: (options: RunOptions) => void }) {
  const set = (change: Partial<RunOptions>) => setOptions({ ...options, ...change })
  const number = (value: string) => Number(value) || 0
  return <>
    <div className="form-grid">
      <Field label="Adapter type" hint="LoKr files are small and reported to bleed less between characters.">{(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} value={options.network} onChange={(event) => set({ network: event.target.value as RunOptions['network'] })}>
          <option value="lokr">LoKr</option><option value="lora">LoRA</option>
        </select>
      )}</Field>
      {options.network === 'lora' && <TextInput label="Rank" type="number" value={String(options.rank)} onChange={(value) => set({ rank: number(value) })} />}
      <TextInput label="Steps" type="number" value={String(options.steps)} onChange={(value) => set({ steps: number(value) })} hint="Reports range from 500 to 3,500; 3,000 or more may overfit." />
      <TextInput label="Save a checkpoint every" type="number" value={String(options.save_every)} onChange={(value) => set({ save_every: number(value) })} hint="Steps. Checkpoints are what a run can resume from." />
      <TextInput label="Learning rate" value={String(options.learning_rate)} onChange={(value) => set({ learning_rate: Number(value) || options.learning_rate })} />
      <Field label="Resolution">{(id) => (
        <select id={id} value={options.resolution} onChange={(event) => set({ resolution: Number(event.target.value) as RunOptions['resolution'] })}>
          <option value={1024}>512 and 1024</option><option value={512}>512 only (less memory)</option>
        </select>
      )}</Field>
    </div>
    <Toggle label="Low memory mode" checked={options.low_vram} onChange={(low_vram) => set({ low_vram })} hint="Slower; for GPUs under 24 GB." />
  </>
}

/** Train: real state, reported progress, checkpoints, and cancel, resume or restart. */
export function Train() {
  const runs = useRuns()
  if (!runs.data) return null
  if (runs.data.runs.length === 0) return <p className="subtle">No training yet. Start a run in Configure, or import an adapter in Adopt.</p>
  return <ul className="run-list">{runs.data.runs.map((run) => <RunCard key={run.id} run={run} />)}</ul>
}

function RunCard({ run }: { run: TrainingRun }) {
  const client = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const act = async (path: string, body: unknown = {}) => {
    setBusy(true)
    try { await api(`/lora/runs/${run.id}/${path}`, body); setError(null) } catch (failed) { setError(failure(failed, 'That did not work.')) } finally { setBusy(false) }
    await client.invalidateQueries({ queryKey: RUNS_KEY })
    await client.invalidateQueries({ queryKey: ADAPTERS_KEY })
  }
  const percent = run.progress_step !== null && run.progress_total ? Math.min(100, (run.progress_step / run.progress_total) * 100) : null
  return (
    <li className="lora-panel run-card">
      <div className="backend-title"><strong>{run.name}</strong><span className="badge">{run.status}</span><span className="subtle">trigger {run.trigger} · {run.options.network} · {run.options.steps} steps · attempt {run.attempt}</span></div>
      <p className={run.status === 'failed' ? 'error-text' : 'subtle'} role="status">{progressLine(run)}</p>
      {percent !== null && run.status === 'running' && <progress max={100} value={percent} aria-label="Reported training progress" />}
      <RunActions run={run} busy={busy} act={act} />
      {error && <Notice tone="error">{error}</Notice>}
      {run.checkpoints.length > 0 && (
        <ul className="plain-list">{run.checkpoints.map((item) => (
          <li key={item.file} className="checkpoint-line">
            <span className={item.verified ? 'subtle' : 'error-text'}>{checkpointLine(item)}</span>
            {item.verified && !item.final && run.status !== 'running' && <button type="button" className="text-button" disabled={busy} onClick={() => void act('keep', { step: item.step })}>Keep as adapter</button>}
          </li>
        ))}</ul>
      )}
      <details><summary className="subtle">Trainer output</summary><pre className="run-log">{run.log_tail || 'Nothing yet.'}</pre><a className="text-button" href={`/api/lora/runs/${run.id}/log`} target="_blank" rel="noreferrer">Full log</a></details>
    </li>
  )
}

function RunActions({ run, busy, act }: { run: TrainingRun; busy: boolean; act: (path: string) => Promise<void> }) {
  if (run.status === 'running') return <div className="post-actions"><button type="button" className="text-button" disabled={busy} onClick={() => void act('cancel')}>Cancel training</button></div>
  return (
    <div className="post-actions">
      {run.resumable && <button type="button" className="text-button" disabled={busy} onClick={() => void act('resume')}>Resume from the last checked checkpoint</button>}
      {run.restartable && <button type="button" className="text-button" disabled={busy} onClick={() => void act('restart')}>Restart from the beginning</button>}
    </div>
  )
}
