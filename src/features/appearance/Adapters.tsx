import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, Trash2 } from 'lucide-react'
import { api, upload } from '../../api'
import type { AppearanceState, LoraAdapter } from '../../types'
import { Notice } from '../../components/Feedback'
import { Field, TextInput } from '../../components/Fields'
import { formatBytes } from './loraState'
import { ADAPTERS_KEY, useAdapters } from './queries'

const APPEARANCE_KEY = ['lora-appearance']
type Result = { tone: 'info' | 'error'; text: string } | null
const failure = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback

/** Adopt: compare versions and deliberately choose how future images draw the character. */
export function Adopt() {
  const client = useQueryClient()
  const adapters = useAdapters()
  const appearance = useQuery({ queryKey: APPEARANCE_KEY, queryFn: () => api<AppearanceState>('/lora/appearance') })
  const [result, setResult] = useState<Result>(null)
  const refresh = async () => {
    await client.invalidateQueries({ queryKey: ADAPTERS_KEY })
    await client.invalidateQueries({ queryKey: APPEARANCE_KEY })
  }
  const adopt = async (body: Record<string, unknown>) => {
    try {
      const adopted = await api<AppearanceState>('/lora/appearance', body)
      setResult({ tone: 'info', text: adopted.install && !adopted.install.installed ? `Adopted. ${adopted.install.note}` : `Adopted as appearance version ${adopted.current.number}. Images requested from now on use it; earlier images keep theirs.` })
    } catch (error) { setResult({ tone: 'error', text: failure(error, 'Not adopted.') }) }
    await refresh()
  }
  if (!adapters.data || !appearance.data) return null
  const current = appearance.data.current
  return (
    <div className="form-stack">
      <Notice>{current.method === 'lora' && current.adapter ? `Images now use ${current.adapter.name} at strength ${current.strength} on ComfyUI (appearance version ${current.number}). Codex and image APIs still draw from the description.` : 'Images now draw the character from the appearance description.'}</Notice>
      {current.method === 'lora' && <div className="form-actions"><button type="button" className="button" onClick={() => void adopt({ method: 'text', note: 'Back to the description' })}>Use the description only</button></div>}
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
      <ul className="run-list">{adapters.data.adapters.map((adapter) => (
        <AdapterCard key={adapter.id} adapter={adapter} current={current.adapter_id === adapter.id} adopt={adopt} refresh={refresh} setResult={setResult} />
      ))}</ul>
      <ImportAdapter refresh={refresh} setResult={setResult} />
      <History state={appearance.data} />
    </div>
  )
}

function AdapterCard({ adapter, current, adopt, refresh, setResult }: { adapter: LoraAdapter; current: boolean; adopt: (body: Record<string, unknown>) => Promise<void>; refresh: () => Promise<void>; setResult: (result: Result) => void }) {
  const [strength, setStrength] = useState('1')
  const remove = async () => {
    try { await api(`/lora/adapters/${adapter.id}`, undefined, 'DELETE') } catch (error) { setResult({ tone: 'error', text: failure(error, 'Not removed.') }) }
    await refresh()
  }
  return (
    <li className="lora-panel">
      <div className="backend-title"><strong>{adapter.name}</strong>{current && <span className="badge">In use</span>}<span className="badge">{adapter.format}</span>{!adapter.available && <span className="badge">Removed</span>}</div>
      <p className="subtle">{adapter.origin === 'trained' ? `Trained${adapter.step !== null ? ` to step ${adapter.step}` : ''} with ${adapter.trainer}` : 'Imported'} · base {adapter.base_model} · trigger {adapter.trigger || 'none'} · {formatBytes(adapter.bytes)}</p>
      {adapter.license_note && <p className="subtle">{adapter.license_note}</p>}
      {adapter.available && (
        <div className="post-actions">
          <div className="lora-strength"><TextInput label="Strength" type="number" value={strength} onChange={setStrength} /></div>
          <button type="button" className="button" onClick={() => void adopt({ method: 'lora', adapter_id: adapter.id, strength: Number(strength) || 1 })}>Adopt for future images</button>
          <a className="text-button" href={`/api/lora/adapters/${adapter.id}/export`} download><Download aria-hidden="true" />Export</a>
          {!current && <button type="button" className="text-button danger-text" onClick={() => void remove()}><Trash2 aria-hidden="true" />Remove</button>}
        </div>
      )}
    </li>
  )
}

function ImportAdapter({ refresh, setResult }: { refresh: () => Promise<void>; setResult: (result: Result) => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [name, setName] = useState('')
  const [base, setBase] = useState('krea/Krea-2-Raw')
  const [trigger, setTrigger] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!file) return
    setBusy(true)
    try {
      await upload('/lora/adapters/import', file, { name: name || file.name.replace(/\.safetensors$/i, ''), base_model: base, trigger })
      setResult({ tone: 'info', text: 'Imported. Evaluate it, then adopt it if it looks right.' })
      setFile(null)
    } catch (error) { setResult({ tone: 'error', text: failure(error, 'Not imported.') }) } finally { setBusy(false) }
    await refresh()
  }
  return (
    <form className="form-stack lora-panel" onSubmit={submit}>
      <h3>Import an adapter</h3>
      <p className="subtle">Already have a LoRA or LoKr for this character? Bring it in instead of training. It must be a .safetensors file for the model your ComfyUI workflow uses.</p>
      <Field label="Adapter file">{(id) => <input id={id} type="file" accept=".safetensors" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />}</Field>
      <div className="form-grid">
        <TextInput label="Name" value={name} maxLength={120} onChange={setName} />
        <TextInput label="Base model it was trained on" value={base} maxLength={300} onChange={setBase} />
        <TextInput label="Trigger word" value={trigger} maxLength={100} onChange={setTrigger} />
      </div>
      <div className="form-actions"><button type="submit" className="button" disabled={!file || busy || !base.trim()}>{busy ? 'Importing' : 'Import'}</button></div>
    </form>
  )
}

function History({ state }: { state: AppearanceState }) {
  if (state.versions.length === 0) return null
  return (
    <details className="versions">
      <summary>Appearance versions ({state.versions.length})</summary>
      <ol reversed>{state.versions.map((version) => (
        <li key={version.id}>
          <span>Version {version.number}{version.current ? ' (current)' : ''}: {version.method === 'lora' ? `${version.adapter?.name ?? 'adapter'} at ${version.strength}` : 'appearance description'}</span>
          <small>{version.adopted_at ? new Date(version.adopted_at).toLocaleString() : ''}{version.note ? ` · ${version.note}` : ''}</small>
        </li>
      ))}</ol>
    </details>
  )
}
