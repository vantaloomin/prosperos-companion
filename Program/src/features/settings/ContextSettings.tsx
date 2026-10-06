import { useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Trash2 } from 'lucide-react'
import { api } from '../../api'
import type { ArgumentSource, ContextCategory, ContextMapping, ContextOverview, ContextPurpose, ContextServiceInfo, MappingSuggestion, Observation, ToolArgument } from '../../types'
import { Notice } from '../../components/Feedback'
import { BuiltinCulture } from './BuiltinCulture'
import { BuiltinPulse } from './BuiltinPulse'
import { BuiltinWeather } from './BuiltinWeather'
import { Field, TextArea, TextInput, Toggle } from '../../components/Fields'
import { CATEGORY_LABELS, CATEGORY_ORDER, CONTEXT_KEY, SEARCH_PRESETS, SOURCE_LABELS, canSave, canTry, purposeLabel, initialMapping, missingArguments, observationSummary, serviceBody, sourcesFor, withPurpose, withSource, type MappingDraft, type ServiceDraft } from './contextTools'

type Result = { tone: 'info' | 'error'; text: string } | null
type Overview = ContextOverview
const failure = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback

/** Real weather, news and local events through MCP servers you add (PRD X1–X3). Nothing runs until you turn a lookup on. */
export function ContextSettings({ name }: { name: string }) {
  const client = useQueryClient()
  const overview = useQuery({ queryKey: CONTEXT_KEY, queryFn: () => api<Overview>('/context') })
  const [adding, setAdding] = useState(false)
  const [result, setResult] = useState<Result>(null)
  const refresh = () => client.invalidateQueries({ queryKey: CONTEXT_KEY })
  if (!overview.data) return null
  const data = overview.data
  return (
    <section className="settings-section form-stack" aria-labelledby="context-heading">
      <div>
        <h2 id="context-heading">Real-world lookups</h2>
        <p className="subtle">
          {name} can check real weather, news and local events when you ask about them, through MCP servers you add. Lookups send only what you approve below,
          never your conversation or memories, and results are treated as outside information that can be out of date.
        </p>
      </div>
      <LocationForm data={data} setResult={setResult} />
      <LinkReading data={data} name={name} setResult={setResult} />
      {data.services.length === 0 && <p className="subtle">No lookup service is set up. {name} answers from what they already know. The built-in weather, local pulse and culture pulse servers need no key or account.</p>}
      <ol className="backend-list">
        {data.services.map((service) => <ServiceRow key={service.id} service={service} data={data} name={name} refresh={refresh} setResult={setResult} />)}
      </ol>
      <SearchPresets data={data} refresh={refresh} setResult={setResult} />
      {adding ? <AddService onDone={() => { setAdding(false); void refresh() }} setResult={setResult} />
        : <div className="form-actions">
          {(['weather', 'pulse', 'culture'] as const).filter((kind) => !data.services.some((service) => service.builtin === kind))
            .map((kind) => <AddBuiltin key={kind} kind={kind} refresh={refresh} setResult={setResult} />)}
          <button type="button" className="button" onClick={() => setAdding(true)}>Add a lookup service</button>
        </div>}
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
    </section>
  )
}

/** One-click hosted search services. Adding one connects and lists its tools; nothing is searched until approved. */
function SearchPresets({ data, refresh, setResult }: { data: Overview; refresh: () => Promise<unknown>; setResult: (result: Result) => void }) {
  const [busy, setBusy] = useState(false)
  const missing = SEARCH_PRESETS.filter((preset) => !data.services.some((service) => service.url === preset.url))
  if (missing.length === 0) return null
  const add = async (preset: string, label: string) => {
    if (busy) return
    setBusy(true)
    try {
      const created = await api<ContextServiceInfo>('/context/services/preset', { preset })
      const checked = await api<ContextServiceInfo>(`/context/services/${created.id}/check`, {})
      setResult(checked.check_error ? { tone: 'error', text: `Added ${label}, but the check failed: ${checked.check_error}` } : { tone: 'info', text: `Added ${label}. Review and turn on its web search or link reading below.` })
      await refresh()
    } catch (error) { setResult({ tone: 'error', text: failure(error, 'Not added.') }) } finally { setBusy(false) }
  }
  return (
    <div className="form-stack">
      <p className="subtle">Web search: add a hosted search service that works without a key. Searches send only what you asked to look up.</p>
      <ul className="preset-list">
        {missing.map((preset) => (
          <li key={preset.id}>
            <button type="button" className="button" aria-disabled={busy} onClick={() => void add(preset.id, preset.name)}>Add {preset.name}</button>
            <span className="subtle">{preset.note}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

const BUILTINS = {
  weather: { label: 'the built-in weather server', next: 'Review and turn on its weather lookup below.' },
  pulse: { label: 'the built-in local pulse server', next: 'Turn on headlines or games below.' },
  culture: { label: 'the built-in culture pulse server', next: "Turn on movies, shows, games and what's trending below." },
}

/** A keyless server that ships with the app: added and checked in one step, still off until you approve it. */
function AddBuiltin({ kind, refresh, setResult }: { kind: keyof typeof BUILTINS; refresh: () => Promise<unknown>; setResult: (result: Result) => void }) {
  const [busy, setBusy] = useState(false)
  const add = async () => {
    if (busy) return
    setBusy(true)
    try {
      const created = await api<ContextServiceInfo>('/context/services/builtin', { kind })
      const checked = await api<ContextServiceInfo>(`/context/services/${created.id}/check`, {})
      setResult(checked.check_error ? { tone: 'error', text: `Added, but the check failed: ${checked.check_error}` } : { tone: 'info', text: `Added ${BUILTINS[kind].label}. ${BUILTINS[kind].next}` })
      await refresh()
    } catch (error) { setResult({ tone: 'error', text: failure(error, 'Not added.') }) } finally { setBusy(false) }
  }
  return <button type="button" className={kind === 'weather' ? 'button primary' : 'button'} aria-disabled={busy} onClick={() => void add()}>Add {BUILTINS[kind].label}</button>
}

/** Links pasted in chat are opened on this computer, so the companion can talk about them. */
function LinkReading({ data, name, setResult }: { data: Overview; name: string; setResult: (result: Result) => void }) {
  const client = useQueryClient()
  const save = async (value: boolean) => {
    try {
      await api('/context/links', { read_links: value }, 'PUT')
      await client.invalidateQueries({ queryKey: CONTEXT_KEY })
    } catch (error) { setResult({ tone: 'error', text: failure(error, 'Not saved.') }) }
  }
  return <Toggle label="Open links I paste" checked={data.location.read_links} onChange={(value) => void save(value)}
    hint={`So ${name} can talk about them. This computer opens the page, like your browser would; Reddit and X posts are read through their public embeds. A link to your own computer or home network is never opened.`} />
}

function LocationForm({ data, setResult }: { data: Overview; setResult: (result: Result) => void }) {
  const client = useQueryClient()
  const [place, setPlace] = useState<string | null>(null)
  const [latitude, setLatitude] = useState<string | null>(null)
  const [longitude, setLongitude] = useState<string | null>(null)
  const dirty = place !== null || latitude !== null || longitude !== null
  const number = (draft: string | null, saved: number | null) => {
    const text = draft ?? (saved === null ? '' : String(saved))
    return text.trim() === '' ? null : Number(text)
  }
  const save = async (event: FormEvent) => {
    event.preventDefault()
    try {
      await api('/context/location', { user_place: place ?? data.location.user_place, user_latitude: number(latitude, data.location.user_latitude), user_longitude: number(longitude, data.location.user_longitude) }, 'PUT')
      setPlace(null); setLatitude(null); setLongitude(null)
      setResult({ tone: 'info', text: 'Location saved.' })
      await client.invalidateQueries({ queryKey: CONTEXT_KEY })
    } catch (error) { setResult({ tone: 'error', text: failure(error, 'Location not saved.') }) }
  }
  return (
    <form className="form-stack" onSubmit={save}>
      <TextInput label="Your city or region" value={place ?? data.location.user_place} maxLength={120} placeholder="Baltimore, MD" onChange={setPlace}
        hint="Where you are, for weather and events near you. It is separate from where your companion lives, and is never detected automatically." />
      <div className="form-grid">
        <TextInput label="Latitude (optional)" value={latitude ?? (data.location.user_latitude === null ? '' : String(data.location.user_latitude))} onChange={setLatitude} hint="Only for services that need coordinates." />
        <TextInput label="Longitude (optional)" value={longitude ?? (data.location.user_longitude === null ? '' : String(data.location.user_longitude))} onChange={setLongitude} />
      </div>
      {dirty && <div className="form-actions"><button type="submit" className="button primary">Save location</button><button type="button" className="button" onClick={() => { setPlace(null); setLatitude(null); setLongitude(null) }}>Cancel</button></div>}
    </form>
  )
}

const BUILTIN_SOURCES = {
  weather: 'Ships with the app; asks Open-Meteo, or the National Weather Service for US places when Open-Meteo fails',
  pulse: 'Ships with the app; asks Google News, Wikipedia, Reddit, ESPN, MLB and Open-Meteo',
  culture: 'Ships with the app; asks Google News, iTunes, Apple Music, TVmaze, Steam, Open Library, Google Trends, Wikipedia and Reddit',
}

function ServiceSummary({ service }: { service: ContextServiceInfo }) {
  const where = service.builtin ? BUILTIN_SOURCES[service.builtin]
    : service.transport === 'http' ? service.url : (service.command ?? []).join(' ')
  const server = service.server_info ? `${service.server_info.name} · MCP ${service.server_info.protocol}` : ''
  return <>
    <div className="backend-title">
      <strong>{service.name}</strong>
      <span className="badge">{service.builtin ? 'Built in' : service.transport === 'http' ? 'HTTP' : 'Local program'}</span>
      {service.mappings.some((mapping) => mapping.enabled && mapping.approved) && <span className="badge">On</span>}
    </div>
    <p className="subtle">{[where, service.has_key ? 'key saved' : '', server].filter(Boolean).join(' · ')}</p>
  </>
}

function ServiceRow({ service, data, name, refresh, setResult }: { service: ContextServiceInfo; data: Overview; name: string; refresh: () => Promise<unknown>; setResult: (result: Result) => void }) {
  const [busy, setBusy] = useState(false)
  // Busy buttons are marked, not disabled: disabling the focused button would drop keyboard focus.
  const check = async () => {
    if (busy) return
    setBusy(true)
    try {
      const checked = await api<ContextServiceInfo>(`/context/services/${service.id}/check`, {})
      setResult(checked.check_error ? { tone: 'error', text: checked.check_error } : { tone: 'info', text: `${checked.tools.length} tools found on ${service.name}.` })
      await refresh()
    } catch (error) { setResult({ tone: 'error', text: failure(error, 'The check failed.') }) } finally { setBusy(false) }
  }
  const remove = async () => {
    if (busy) return
    setBusy(true)
    try { await api(`/context/services/${service.id}`, undefined, 'DELETE'); await refresh() } catch (error) { setResult({ tone: 'error', text: failure(error, 'Not removed.') }) } finally { setBusy(false) }
  }
  return (
    <li className="backend-row">
      <ServiceSummary service={service} />
      {service.check_error && <Notice tone="error">{service.check_error}</Notice>}
      {!service.checked_at && <p className="subtle">Check the service to see its tools. Checking connects and lists tools; it looks nothing up.</p>}
      {service.tools.length > 0 && (service.builtin ? <>
        {service.builtin === 'weather' ? <BuiltinWeather service={service} data={data} name={name} refresh={refresh} onError={(text) => setResult({ tone: 'error', text })} />
          : service.builtin === 'pulse' ? <BuiltinPulse service={service} data={data} name={name} refresh={refresh} onError={(text) => setResult({ tone: 'error', text })} />
          : <BuiltinCulture service={service} name={name} refresh={refresh} onError={(text) => setResult({ tone: 'error', text })} />}
        <details className="advanced">
          <summary>Advanced</summary>
          <Mappings service={service} data={data} name={name} refresh={refresh} setResult={setResult} />
        </details>
      </> : <Mappings service={service} data={data} name={name} refresh={refresh} setResult={setResult} />)}
      <div className="post-actions">
        <button type="button" className="text-button" aria-disabled={busy} onClick={() => void check()}>{service.checked_at ? 'Check again' : 'Check'}</button>
        <button type="button" className="text-button danger-text" aria-disabled={busy} onClick={() => void remove()}><Trash2 aria-hidden="true" />Remove</button>
      </div>
    </li>
  )
}

function Mappings({ service, data, name, refresh, setResult }: { service: ContextServiceInfo; data: Overview; name: string; refresh: () => Promise<unknown>; setResult: (result: Result) => void }) {
  return <>{CATEGORY_ORDER.map((category) => (
    <CategoryMapping key={category} category={category} service={service} data={data} name={name} suggestion={service.suggestions[category]}
      saved={service.mappings.find((mapping) => mapping.category === category)} refresh={refresh} setResult={setResult} />
  ))}</>
}

interface MappingProps {
  category: ContextCategory
  service: ContextServiceInfo
  data: Overview
  name: string
  suggestion?: MappingSuggestion
  saved?: ContextMapping
  refresh: () => Promise<unknown>
  setResult: (result: Result) => void
}

function CategoryMapping(props: MappingProps) {
  const { category, service, data, name, suggestion, saved, refresh, setResult } = props
  const [editing, setEditing] = useState(false)
  const [busy, setBusy] = useState(false)
  const act = async (action: () => Promise<unknown>) => {
    if (busy) return false
    setBusy(true)
    try { await action(); await refresh(); setResult(null); return true } catch (error) { setResult({ tone: 'error', text: failure(error, 'That did not work.') }); return false } finally { setBusy(false) }
  }
  const path = `/context/services/${service.id}/tools/${category}`
  if (editing) {
    return <MappingEditor category={category} service={service} data={data} name={name} draft={initialMapping(service.tools, saved, suggestion)} busy={busy}
      onCancel={() => setEditing(false)} onSave={async (draft) => { if (await act(() => api(path, draft, 'PUT'))) setEditing(false) }} />
  }
  if (saved) return <SavedMapping category={category} mapping={saved} path={path} name={name} busy={busy} act={act} onEdit={() => setEditing(true)} />
  if (!suggestion) return null
  return (
    <div className="context-mapping">
      <p className="subtle">{CATEGORY_LABELS[category]}: “{suggestion.tool}” looks suitable.</p>
      <div className="post-actions"><button type="button" className="text-button" onClick={() => setEditing(true)}>Set up {CATEGORY_LABELS[category].toLowerCase()}</button></div>
    </div>
  )
}

interface SavedProps { category: ContextCategory; mapping: ContextMapping; path: string; name: string; busy: boolean; act: (action: () => Promise<unknown>) => Promise<boolean>; onEdit: () => void }

function SavedMapping({ category, mapping, path, name, busy, act, onEdit }: SavedProps) {
  const [tried, setTried] = useState<Observation[] | null>(null)
  const on = mapping.enabled && mapping.approved
  const tryNow = (purpose: ContextPurpose) => act(async () => {
    setTried((await api<{ observations: Observation[] }>('/context/lookup', { category, purpose })).observations)
  })
  const toggle = (value: boolean) => act(() => value ? api(`${path}/enable`, { digest: mapping.disclosure.digest }) : api(`${path}/disable`, {}))
  return (
    <div className="context-mapping">
      <div className="backend-title">
        <strong>{CATEGORY_LABELS[category]}</strong>
        <span className="badge">{mappingBadge(mapping)}</span>
      </div>
      {on ? <p className="subtle">Sends {mapping.disclosure.sends.map((item) => item.argument).join(', ') || 'nothing'} to “{mapping.tool}”.</p>
        : <ul className="disclosure">{mapping.disclosure.summary.map((line) => <li key={line}>{line}</li>)}</ul>}
      <Toggle label={on ? 'Turned on' : 'Turn on'} checked={on} onChange={(value) => void toggle(value)}
        hint={on ? undefined : 'Turning it on confirms what it sends, as described above. Any later change asks again.'} />
      {tried && <TryResults items={tried} />}
      <div className="post-actions">
        {on && canTry(category) && mapping.run_in.map((purpose) => (
          <button key={purpose} type="button" className="text-button" aria-disabled={busy} onClick={() => void tryNow(purpose)}>
            {purpose === 'conversation' ? 'Try it for your location' : `Try it for ${name}'s city`}
          </button>
        ))}
        <button type="button" className="text-button" aria-disabled={busy} onClick={() => !busy && onEdit()}>Edit</button>
        <button type="button" className="text-button danger-text" aria-disabled={busy} onClick={() => void act(() => api(path, undefined, 'DELETE'))}>Stop using</button>
      </div>
    </div>
  )
}

function mappingBadge(mapping: ContextMapping): string {
  if (mapping.enabled && mapping.approved) return 'On'
  return mapping.enabled ? 'Changed: review again' : 'Off'
}

function TryResults({ items }: { items: Observation[] }) {
  if (!items.length) return <p className="subtle">Nothing was looked up: set your location first, or the companion's city is not a real place.</p>
  return (
    <ul className="lookup-list">
      {items.map((item) => {
        const summary = observationSummary(item)
        return <li key={item.id}><strong>{summary.state}</strong>{item.content && <p className="lookup-content">{item.content}</p>}</li>
      })}
    </ul>
  )
}

interface EditorProps { category: ContextCategory; service: ContextServiceInfo; data: Overview; name: string; draft: MappingDraft; busy: boolean; onCancel: () => void; onSave: (draft: MappingDraft) => void }

function MappingEditor({ category, service, data, name, draft: initial, busy, onCancel, onSave }: EditorProps) {
  const [draft, setDraft] = useState(initial)
  const tool = service.tools.find((item) => item.name === draft.tool)
  const properties = Object.entries(tool?.input_schema.properties ?? {})
  const required = new Set(tool?.input_schema.required ?? [])
  const missing = missingArguments(tool, draft.arguments)
  return (
    <div className="context-mapping form-stack">
      <strong>{CATEGORY_LABELS[category]}</strong>
      <Field label="Tool">{(id) => (
        <select id={id} value={draft.tool} onChange={(event) => setDraft({ tool: event.target.value, arguments: {}, run_in: draft.run_in })}>
          {service.tools.map((item) => <option key={item.name} value={item.name}>{item.name}</option>)}
        </select>
      )}</Field>
      <p className="subtle">{tool?.description || (properties.length ? '' : 'This tool takes no arguments.')}</p>
      {properties.map(([property, schema]) => (
        <ArgumentRow key={property} category={category} property={property} description={schema.description} required={required.has(property)}
          argument={draft.arguments[property]} onSource={(source) => setDraft(withSource(draft, property, source))}
          onValue={(value) => setDraft({ ...draft, arguments: { ...draft.arguments, [property]: { source: 'literal', value } } })} />
      ))}
      {data.categories[category].purposes.map((purpose) => (
        <Toggle key={purpose} label={purposeLabel(category, purpose, name)}
          hint={data.purposes[purpose]} checked={draft.run_in.includes(purpose)} onChange={(value) => setDraft(withPurpose(draft, purpose, value))} />
      ))}
      {missing.length > 0 && <p className="subtle">The tool needs {missing.join(', ')}.</p>}
      <p className="subtle">Saving keeps it off. You will see exactly what it sends before turning it on.</p>
      <div className="form-actions">
        <button type="button" className="button primary" disabled={busy || !canSave(draft, tool)} onClick={() => onSave(draft)}>Save</button>
        <button type="button" className="button" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  )
}

interface ArgumentProps { category: ContextCategory; property: string; description?: string; required: boolean; argument?: ToolArgument; onSource: (source: ArgumentSource | '') => void; onValue: (value: string) => void }

function ArgumentRow({ category, property, description, required, argument, onSource, onValue }: ArgumentProps) {
  return (
    <div className="form-grid">
      <Field label={required ? `${property} (required)` : property} hint={description}>{(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} value={argument?.source ?? ''} onChange={(event) => onSource(event.target.value as ArgumentSource | '')}>
          <option value="">Not sent</option>
          {sourcesFor(category).map((source) => <option key={source} value={source}>{SOURCE_LABELS[source]}</option>)}
        </select>
      )}</Field>
      {argument?.source === 'literal' && <TextInput label="Value" value={String(argument.value ?? '')} maxLength={200} onChange={onValue} />}
    </div>
  )
}

function AddService({ onDone, setResult }: { onDone: () => void; setResult: (result: Result) => void }) {
  const [draft, setDraft] = useState<ServiceDraft>({ name: '', transport: 'stdio', program: '', args: '', url: '', secret: '', secretName: '' })
  const [busy, setBusy] = useState(false)
  const set = (change: Partial<ServiceDraft>) => setDraft({ ...draft, ...change })
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    try {
      const created = await api<ContextServiceInfo>('/context/services', serviceBody(draft))
      const checked = await api<ContextServiceInfo>(`/context/services/${created.id}/check`, {})
      setResult(checked.check_error ? { tone: 'error', text: `Added, but the check failed: ${checked.check_error}` } : { tone: 'info', text: `Added ${created.name} with ${checked.tools.length} tools. Set up a lookup below.` })
      onDone()
    } catch (error) { setResult({ tone: 'error', text: failure(error, 'Not added.') }) } finally { setBusy(false) }
  }
  return (
    <form className="form-stack add-backend" onSubmit={submit}>
      <TextInput label="Name" value={draft.name} required maxLength={80} placeholder="Weather" onChange={(name) => set({ name })} />
      <Field label="How it runs">{(id) => (
        <select id={id} value={draft.transport} onChange={(event) => set({ transport: event.target.value as ServiceDraft['transport'] })}>
          <option value="stdio">A program on this computer (stdio)</option>
          <option value="http">A server address (streamable HTTP)</option>
        </select>
      )}</Field>
      {draft.transport === 'stdio' ? <>
        <TextInput label="Program" value={draft.program} required maxLength={1000} placeholder="C:\Tools\weather-mcp.exe" onChange={(program) => set({ program })}
          hint="The app starts it only to check it or look something up, with a short time limit." />
        <TextArea label="Arguments, one per line" value={draft.args} rows={2} onChange={(args) => set({ args })} />
      </> : (
        <TextInput label="Server address" value={draft.url} required maxLength={2000} placeholder="https://example.com/mcp" onChange={(url) => set({ url })}
          hint="HTTPS, or HTTP for a server on this computer." />
      )}
      <div className="form-grid">
        <TextInput label="Key (optional)" type="password" value={draft.secret} maxLength={4000} onChange={(secret) => set({ secret })} hint="Kept in your system's credential store and sent only to this service." />
        <TextInput label={draft.transport === 'stdio' ? 'Environment variable for the key' : 'Header for the key'} value={draft.secretName} maxLength={100}
          placeholder={draft.transport === 'stdio' ? 'API_KEY' : 'Authorization'} onChange={(secretName) => set({ secretName })} />
      </div>
      <div className="form-actions">
        <button type="submit" className="button primary" disabled={busy}>Add and check</button>
        <button type="button" className="button" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}
