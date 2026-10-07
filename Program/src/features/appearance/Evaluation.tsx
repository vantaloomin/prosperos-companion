import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { EvalImage, Evaluation } from '../../types'
import { Notice } from '../../components/Feedback'
import { Field, TextInput, Toggle } from '../../components/Fields'
import { evaluationRows } from './loraState'
import { pictureUrl, useAdapters } from './queries'

const EVALUATIONS_KEY = ['lora-evaluations']
const failure = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback

/** Evaluate: a fixed set rendered on local ComfyUI, with the adapter and from text alone. Nothing is hidden. */
export function Evaluate() {
  const evaluations = useQuery({
    queryKey: EVALUATIONS_KEY, queryFn: () => api<{ evaluations: Evaluation[] }>('/lora/evaluations'),
    refetchInterval: (query) => query.state.data?.evaluations.some((item) => item.status === 'running') ? 2000 : false,
  })
  return (
    <div className="form-stack">
      <p className="subtle">Each evaluation renders the same eight prompts with fixed seeds on your local ComfyUI server: portrait, full body, two everyday scenes, two kinds of light, an expression and the key traits from the appearance description. Each is also drawn from the text description alone, so you can see what the adapter adds. Every result and failure stays listed. Pictures you held back are shown beside them for comparison; they are never used to make images.</p>
      <StartEvaluation />
      {(evaluations.data?.evaluations ?? []).map((item) => <EvaluationView key={item.id} evaluation={item} />)}
    </div>
  )
}

function StartEvaluation() {
  const client = useQueryClient()
  const adapters = useAdapters()
  const available = (adapters.data?.adapters ?? []).filter((adapter) => adapter.available)
  const [adapterId, setAdapterId] = useState('')
  const [strength, setStrength] = useState('1')
  const [baseline, setBaseline] = useState(true)
  const [result, setResult] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const chosen = adapterId || available[0]?.id || ''
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    try {
      const created = await api<Evaluation>('/lora/evaluations', { adapter_id: chosen, strength: Number(strength) || 1, include_baseline: baseline })
      setResult(created.install && !created.install.installed ? { tone: 'info', text: created.install.note } : null)
      await client.invalidateQueries({ queryKey: EVALUATIONS_KEY })
    } catch (error) { setResult({ tone: 'error', text: failure(error, 'The evaluation did not start.') }) }
  }
  if (available.length === 0) return <p className="subtle">There is no adapter to evaluate yet. Train one, or import one in Adopt.</p>
  return (
    <form className="form-stack lora-panel" onSubmit={submit}>
      <div className="form-grid">
        <Field label="Adapter">{(id, hint) => (
          <select id={id} aria-describedby={hint} value={chosen} onChange={(event) => setAdapterId(event.target.value)}>
            {available.map((adapter) => <option key={adapter.id} value={adapter.id}>{adapter.name}</option>)}
          </select>
        )}</Field>
        <TextInput label="Strength" type="number" value={strength} onChange={setStrength} hint="0 to 2; 1 is the trained strength." />
      </div>
      <Toggle label="Also draw each prompt from the text description" checked={baseline} onChange={setBaseline} hint="Pictures without the adapter, side by side, to show what it adds." />
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
      <div className="form-actions"><button type="submit" className="button primary">Render the evaluation set</button></div>
    </form>
  )
}

function EvaluationView({ evaluation }: { evaluation: Evaluation }) {
  const client = useQueryClient()
  const { counts } = evaluation
  const summary = `${counts.completed} made, ${counts.failed} failed${counts.queued + counts.running ? `, ${counts.queued + counts.running} to go` : ''}${counts.cancelled + counts.interrupted ? `, ${counts.cancelled + counts.interrupted} stopped` : ''}.`
  const refresh = () => client.invalidateQueries({ queryKey: EVALUATIONS_KEY })
  return (
    <section className="lora-panel">
      <div className="backend-title"><strong>{evaluation.adapter.name}</strong><span className="badge">{evaluation.status}</span><span className="subtle">strength {evaluation.strength} · set {evaluation.set_version} · {new Date(evaluation.created_at).toLocaleString()}</span></div>
      <p className="subtle" role="status">{summary}</p>
      {evaluation.status === 'running' && <button type="button" className="text-button" onClick={() => void api(`/lora/evaluations/${evaluation.id}/cancel`, {}).then(refresh)}>Stop</button>}
      {evaluation.held_out.length > 0 && (
        <div className="held-out"><span className="subtle">Held-out references</span>{evaluation.held_out.map((id) => <img key={id} src={pictureUrl(id)} alt="Held-out reference" loading="lazy" />)}</div>
      )}
      <table className="eval-table">
        <thead><tr><th scope="col">Prompt</th><th scope="col">With the adapter</th><th scope="col">Text description only</th></tr></thead>
        <tbody>{evaluationRows(evaluation.images).map((row) => (
          <tr key={row.key}><th scope="row">{row.label}</th><td><EvalCell image={row.lora} refresh={refresh} /></td><td><EvalCell image={row.text} refresh={refresh} /></td></tr>
        ))}</tbody>
      </table>
    </section>
  )
}

function EvalCell({ image, refresh }: { image?: EvalImage; refresh: () => Promise<unknown> }) {
  if (!image) return <span className="subtle">Not drawn</span>
  const rate = (rating: EvalImage['rating']) => api(`/lora/evaluation-images/${image.id}/rating`, { rating: image.rating === rating ? '' : rating }, 'PUT').then(refresh)
  return (
    <figure className="eval-cell">
      {image.has_image ? <img src={`/api/lora/evaluation-images/${image.id}/file`} alt={`${image.label}, ${image.variant === 'lora' ? 'with the adapter' : 'text only'}`} loading="lazy" />
        : <p className={image.status === 'failed' ? 'error-text' : 'subtle'}>{image.error ?? image.status}</p>}
      <figcaption className="subtle">Seed {image.seed} · {image.width}×{image.height}{image.workflow ? ` · ${image.workflow}` : ''}</figcaption>
      {image.status === 'completed' && (
        <div className="post-actions">
          <button type="button" className="text-button" aria-pressed={image.rating === 'good'} onClick={() => void rate('good')}>Good</button>
          <button type="button" className="text-button" aria-pressed={image.rating === 'weak'} onClick={() => void rate('weak')}>Weak</button>
        </div>
      )}
      <details><summary className="subtle">Prompt</summary><p className="subtle">{image.prompt}</p></details>
    </figure>
  )
}
