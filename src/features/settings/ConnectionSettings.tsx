import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { Connection } from '../../types'
import { Notice } from '../../components/Feedback'
import { TextInput } from '../../components/Fields'

const KEY = ['connection']

export function ConnectionSettings() {
  const connection = useQuery({ queryKey: KEY, queryFn: () => api<{ connection: Connection | null }>('/connection').then((data) => data.connection) })
  if (connection.isPending) return null
  // Not keyed on the saved address: remounting on save would drop the confirmation and keyboard focus.
  return <ConnectionForm saved={connection.data ?? null} />
}

function initialForm(saved: Connection | null) {
  const values = saved ?? { base_url: 'http://127.0.0.1:1234/v1', model: '', max_output_tokens: 800, context_tokens: 16000, timeout_seconds: 180, embedding_model: null }
  return { base_url: values.base_url, model: values.model, api_key: '', max_output_tokens: String(values.max_output_tokens),
    context_tokens: String(values.context_tokens), timeout_seconds: String(values.timeout_seconds), embedding_model: values.embedding_model ?? '' }
}

function keyHint(saved: Connection | null) {
  return saved?.has_key ? 'A key is saved in your system keychain. Leave this empty to keep it.' : 'Only if the service needs one. It is stored in your system keychain, not in the workspace.'
}

function ConnectionForm({ saved }: { saved: Connection | null }) {
  const client = useQueryClient()
  const [form, setForm] = useState(() => initialForm(saved))
  const [result, setResult] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const [saving, setSaving] = useState(false)
  const set = (key: keyof typeof form) => (value: string) => setForm((current) => ({ ...current, [key]: value }))
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (saving) return
    setSaving(true)
    try {
      const body = { base_url: form.base_url.trim(), model: form.model.trim(), api_key: form.api_key || null,
        max_output_tokens: Number(form.max_output_tokens), context_tokens: Number(form.context_tokens), timeout_seconds: Number(form.timeout_seconds),
        embedding_model: form.embedding_model.trim() || null }
      const next = await api<Connection>('/connection', body, 'PUT')
      client.setQueryData(KEY, next)
      setForm((current) => ({ ...current, api_key: '' }))
      setResult({ tone: 'info', text: 'Connection saved. Your next message uses it.' })
    } catch (error) {
      setResult({ tone: 'error', text: error instanceof Error ? error.message : 'The connection was not saved.' })
    } finally { setSaving(false) }
  }
  return (
    <form className="settings-section form-stack" onSubmit={submit} aria-labelledby="connection-heading">
      <div>
        <h2 id="connection-heading">Model connection</h2>
        <p className="subtle">Any OpenAI-compatible service: a local server such as LM Studio or Ollama, or a hosted API. Saving does not contact the service or download anything.</p>
      </div>
      <TextInput label="Address" value={form.base_url} onChange={set('base_url')} required maxLength={500} hint="Usually ends in /v1." />
      <TextInput label="Model" value={form.model} onChange={set('model')} required maxLength={200} placeholder="The model's name at that service" />
      <TextInput label="API key" type="password" value={form.api_key} onChange={set('api_key')} maxLength={4000}
        hint={keyHint(saved)} />
      <TextInput label="Embedding model (optional)" value={form.embedding_model} onChange={set('embedding_model')} maxLength={200}
        hint="Lets recall find related memories even when the words differ, using this service's embeddings. Leave empty to match by keywords only. Nothing is downloaded." />
      <div className="form-grid">
        <TextInput label="Longest reply (tokens)" type="number" value={form.max_output_tokens} onChange={set('max_output_tokens')} required />
        <TextInput label="Context size (tokens)" type="number" value={form.context_tokens} onChange={set('context_tokens')} required hint="What the model can read at once." />
        <TextInput label="Time limit (seconds)" type="number" value={form.timeout_seconds} onChange={set('timeout_seconds')} required />
      </div>
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
      <div className="form-actions"><button type="submit" className="button primary" aria-disabled={saving} disabled={!form.model.trim() || !form.base_url.trim()}>Save connection</button></div>
    </form>
  )
}
