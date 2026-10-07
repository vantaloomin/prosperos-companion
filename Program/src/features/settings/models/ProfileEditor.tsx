// The profile form adapted from prosperos-study src/features/models/ProfileEditor.tsx, ModelDiscovery.tsx and
// useModelDiscovery.ts at bbcbde4. It opens in place in Settings rather than in a dialog.
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Check, PlugZap } from 'lucide-react'
import { api } from '../../../api'
import { Notice } from '../../../components/Feedback'
import { TextInput } from '../../../components/Fields'
import { GenerationSettings } from './GenerationSettings'
import { ModelCombobox } from './ModelCombobox'
import { applyDiscovered, discoveredSettings, profileReady, savedKeyApplies, typedModelSettings, type Discovery } from './discovery'
import { configFor, embeddingProviders, providerOrder, providers, type ModelProfile, type ProfileConfig, type Provider } from './types'

const failure = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback

function useDiscovery(profile?: ModelProfile) {
  const [result, setResult] = useState<Discovery | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const sequence = useRef(0)
  useEffect(() => () => { sequence.current++ }, [])
  const reset = () => { sequence.current++; setResult(null); setError(''); setBusy(false) }
  const connect = async (config: ProfileConfig, key: string, onResult: (value: Discovery) => void) => {
    const request = ++sequence.current
    setBusy(true); setError(''); setResult(null)
    try {
      const value = await api<Discovery>('/models/discover', { config, api_key: key || null, profile_id: profile?.id ?? null })
      if (request !== sequence.current) return
      setResult(value); onResult(value)
    } catch (problem) {
      if (request === sequence.current) setError(failure(problem, 'The connection test failed.'))
    } finally { if (request === sequence.current) setBusy(false) }
  }
  return { result, busy, error, reset, connect }
}

type Patch = (change: Partial<ProfileConfig>) => void
type Discovered = ReturnType<typeof useDiscovery>

function useSave(profile: ModelProfile | undefined, onDone: (saved?: ModelProfile) => void) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const save = async (body: { name: string; config: ProfileConfig; api_key: string | null }) => {
    if (saving) return
    setSaving(true); setError('')
    try {
      onDone(profile
        ? await api<ModelProfile>(`/models/profiles/${profile.id}`, { ...body, expected_revision: profile.revision }, 'PUT')
        : await api<ModelProfile>('/models/profiles', body))
    } catch (problem) { setError(failure(problem, 'The profile was not saved.')) } finally { setSaving(false) }
  }
  return { saving, error, save }
}

function useProfileForm(profile: ModelProfile | undefined) {
  const [name, setName] = useState(profile?.name ?? '')
  const [config, setConfig] = useState<ProfileConfig>(profile?.config ?? configFor('local'))
  const [key, setKey] = useState('')
  const discovery = useDiscovery(profile)
  const patch: Patch = (change) => { if (change.base_url !== undefined) discovery.reset(); setConfig(current => ({ ...current, ...change })) }
  const changeProvider = (provider: Provider) => { discovery.reset(); setConfig(configFor(provider)); setKey('') }
  const changeKey = (value: string) => { discovery.reset(); setKey(value) }
  const test = () => { void discovery.connect(config, key, result => setConfig(current => applyDiscovered(result, current))) }
  return { name, setName, config, key, discovery, patch, changeProvider, changeKey, test, ...readiness(profile, config, key),
    body: { name: name.trim(), config, api_key: key || null } }
}

function readiness(profile: ModelProfile | undefined, config: ProfileConfig, key: string) {
  const savedKey = savedKeyApplies(profile?.config, profile?.has_saved_key ?? false, config)
  const ready = profileReady(config)
  return { savedKey, ready, canSave: ready || !!key.trim() || savedKey }
}

export function ProfileEditor({ profile, onDone }: { profile?: ModelProfile; onDone: (saved?: ModelProfile) => void }) {
  const form = useProfileForm(profile)
  const saving = useSave(profile, onDone)
  const { config, patch, discovery } = form
  const submit = (event: FormEvent) => { event.preventDefault(); if (form.canSave) void saving.save(form.body) }
  return <form className="model-profile-editor form-stack" onSubmit={submit} aria-label={profile ? `Edit ${profile.name}` : 'New model profile'}>
    <ProviderPicker selected={config.provider} onChange={form.changeProvider} />
    <TextInput label="Profile name" value={form.name} onChange={form.setName} maxLength={120} placeholder="Everyday chat, careful drafting…" hint="Leave empty to name it after the provider and model." />
    <ConnectionFields config={config} patch={patch} savedKey={form.savedKey} apiKey={form.key} onKey={form.changeKey} />
    <ModelDiscovery config={config} discovery={discovery} onTest={form.test} patch={patch} />
    <ModelFields config={config} patch={patch} discovery={discovery} />
    <SaveActions ready={form.ready} canSave={form.canSave} saving={saving.saving} error={saving.error} onCancel={() => onDone()} />
  </form>
}

function SaveActions({ ready, canSave, saving, error, onCancel }: { ready: boolean; canSave: boolean; saving: boolean; error: string; onCancel: () => void }) {
  return <>
    {!ready && <p className="subtle">You can save the key now and choose a model later. A profile needs a model before it can do a job.</p>}
    {error && <Notice tone="error">{error}</Notice>}
    <div className="form-actions"><button type="submit" className="button primary" disabled={!canSave} aria-disabled={saving}>{saving ? 'Saving…' : 'Save profile'}</button><button type="button" className="button" onClick={onCancel}>Cancel</button><span className="subtle">Keys are kept in your system keychain, never in the workspace or its backups.</span></div>
  </>
}

function ProviderPicker({ selected, onChange }: { selected: Provider; onChange: (provider: Provider) => void }) {
  return <><fieldset className="provider-picker"><legend>Provider</legend>
    {providerOrder.map(provider => <button key={provider} type="button" className={`button${selected === provider ? ' selected' : ''}`} aria-pressed={selected === provider} onClick={() => onChange(provider)}>{providers[provider].name}</button>)}
  </fieldset><p className="subtle">{providers[selected].description}</p></>
}

function ConnectionFields({ config, patch, savedKey, apiKey, onKey }: { config: ProfileConfig; patch: Patch; savedKey: boolean; apiKey: string; onKey: (value: string) => void }) {
  const local = config.provider === 'local' || config.provider === 'kobold'
  if (config.provider === 'codex') return <p className="subtle">Uses the Codex CLI’s own login; no key is entered here. Codex runs in an empty temporary folder with its shell, plugins, web search and tools turned off.</p>
  return <>
    {(local || config.provider === 'compatible') && <TextInput label="Server address" value={config.base_url} onChange={value => patch({ base_url: value })} maxLength={500} hint={local ? 'An address on this computer. LM Studio and Ollama usually end in /v1.' : 'The API base URL, without /models or /chat/completions.'} />}
    <TokenEntry key={config.provider} saved={savedKey} value={apiKey} onChange={onKey} />
  </>
}

function ModelDiscovery({ config, discovery, onTest, patch }: { config: ProfileConfig; discovery: Discovered; onTest: () => void; patch: Patch }) {
  const models = discovery.result?.model_details ?? []
  const choose = (id: string) => { const model = models.find(item => item.id === id); if (model) patch(discoveredSettings(model, config)) }
  return <section className="model-discovery form-stack" aria-label="Connection and models">
    <TestButton blocked={config.provider === 'compatible' && !config.base_url.trim()} busy={discovery.busy} connected={!!discovery.result} onTest={onTest} />
    {discovery.error && <Notice tone="error">{discovery.error}</Notice>}
    {discovery.result?.note && <p className="subtle">{discovery.result.note}</p>}
    {models.length > 0 && <ModelCombobox models={models} value={models.some(model => model.id === config.model) ? config.model : ''} onChange={choose} />}
  </section>
}

function TestButton({ blocked, busy, connected, onTest }: { blocked: boolean; busy: boolean; connected: boolean; onTest: () => void }) {
  return <div className="form-actions"><button type="button" className="button" disabled={busy || blocked} onClick={onTest}><PlugZap size={16} aria-hidden="true" />{busy ? 'Testing…' : 'Test connection'}</button>{connected && <span className="connection-success" role="status"><Check size={15} aria-hidden="true" />Connected</span>}</div>
}

function ModelFields({ config, patch, discovery }: { config: ProfileConfig; patch: Patch; discovery: Discovered }) {
  const models = discovery.result?.model_details ?? []
  return <>
    <TextInput label="Model ID" value={config.model} onChange={value => patch(typedModelSettings(value.trim(), config, models))} maxLength={200} placeholder="Choose from the list, or type the model's ID"
      hint="Test connection lists the models this service offers. Picking one fills in its settings." tip="The exact name the service uses for the model, such as gpt-4o-mini or llama3.1:8b." />
    {embeddingProviders.includes(config.provider) && <TextInput label="Embedding model (optional)" value={config.embedding_model ?? ''} onChange={value => patch({ embedding_model: value })} maxLength={200} hint="Lets recall find related memories even when the words differ, using this service’s embeddings. EmbeddingGemma 2 and Qwen3 Embedding 0.6B work well; Built-in recall below can run one without this service." />}
    <details className="advanced-settings"><summary>Generation settings</summary><GenerationSettings config={config} patch={patch} model={models.find(model => model.id === config.model)} /></details>
  </>
}

function TokenEntry({ saved, value, onChange }: { saved: boolean; value: string; onChange: (value: string) => void }) {
  const [editing, setEditing] = useState(false)
  if (!editing) return <div className="token-entry"><p>{saved ? 'An API key is saved for this profile.' : 'No API key saved for this profile.'}</p><button type="button" className="button" onClick={() => setEditing(true)}>{saved ? 'Replace key' : 'Add API key'}</button><small>Local servers can leave this empty, and an environment variable such as OPENAI_API_KEY also works.</small></div>
  return <div className="token-entry"><TextInput label="API key" type="password" value={value} onChange={onChange} maxLength={4000} hint="Saved in your system keychain. It is never shown again." /><button type="button" className="text-button" onClick={() => { onChange(''); setEditing(false) }}>Cancel key entry</button></div>
}
