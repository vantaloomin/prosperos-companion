import { useId, useState, type FormEvent, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { api } from '../../api'
import type { ArgumentSource, ContextCategory, ContextMapping, ContextOverview, ContextPurpose, ContextServiceInfo, MappingSuggestion, Observation, ToolArgument, ToolProperty } from '../../types'
import { Notice } from '../../components/Feedback'
import { InfoTip } from '../../components/InfoTip'
import { Menu, type MenuEntry, type MenuItem } from '../../components/Menu'
import { FoldRow, RowGroup, SettingRow, SwitchRow } from '../../components/Rows'
import { BuiltinCulture } from './BuiltinCulture'
import { BuiltinPulse } from './BuiltinPulse'
import { BuiltinWeather } from './BuiltinWeather'
import { Field, TextArea, TextInput, Toggle } from '../../components/Fields'
import { OptionalStepper } from '../../components/NumberFields'
import { CATEGORY_LABELS, CATEGORY_ORDER, CONTEXT_KEY, SEARCH_PRESETS, SOURCE_LABELS, argumentKind, canSave, canTry, propertyLabel, purposeLabel, initialMapping, missingArguments, observationSummary, serviceBody, sourcesFor, withAppFilled, withPurpose, withSource, type MappingDraft, type ServiceDraft } from './contextTools'
import { SectionPending } from '../../components/SectionPending'
import { countText } from '../../components/numberBounds'
import { canTurnOn, serviceIsOn, setServiceOn } from './builtinSave'

type Result = { tone: 'info' | 'error'; text: string } | null
type Overview = ContextOverview
const failure = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback

/** Real weather, news and local events through MCP servers you add (PRD X1–X3). Nothing runs until you turn a lookup on.
 * Style guide: where you are and links as rows, then the lookup services as fold rows with one Add menu. */
export function ContextSettings({ name }: { name: string }) {
  const client = useQueryClient()
  const overview = useQuery({ queryKey: CONTEXT_KEY, queryFn: () => api<Overview>('/context') })
  const [adding, setAdding] = useState(false)
  const [result, setResult] = useState<Result>(null)
  const refresh = () => client.invalidateQueries({ queryKey: CONTEXT_KEY })
  if (!overview.data) return <SectionPending queries={[overview]} heading="context-heading" title="Real-world lookups" />
  const data = overview.data
  return <>
    <RowGroup id="location-heading">
      <PlaceRow data={data} setResult={setResult} />
      <LinkReading data={data} name={name} setResult={setResult} />
      <Coordinates data={data} setResult={setResult} />
    </RowGroup>
    <section className="row-group" aria-labelledby="context-heading">
      <div className="row-group-head">
        <h2 id="context-heading" className="section-title">Lookups<InfoTip id="context-tip" label="Lookups"
          text={`${name} can check real weather, news and local events when you ask about them, through MCP servers you add. Lookups send only what you approve, never your conversation or memories, and results are treated as outside information that can be out of date.`} /></h2>
        <AddLookup data={data} refresh={refresh} setResult={setResult} onOther={() => setAdding(true)} />
      </div>
      <div className="row-list">
        {data.services.length === 0
          ? <p className="setting-row row-empty">No lookup service yet. {name} answers from what they already know. The built-in ones need no key or account.</p>
          : <ol className="backend-list">{data.services.map((service) => <ServiceRow key={service.id} service={service} data={data} name={name} refresh={refresh} setResult={setResult} />)}</ol>}
      </div>
      {adding && <AddService onDone={() => { setAdding(false); void refresh() }} setResult={setResult} />}
    </section>
    {result && <Notice tone={result.tone}>{result.text}</Notice>}
  </>
}

const BUILTINS = {
  weather: { label: 'Weather', added: 'the built-in weather server', next: 'Review and turn on its weather lookup below.' },
  pulse: { label: 'Local events and sports', added: 'the built-in local pulse server', next: 'Turn on headlines or games below.' },
  culture: { label: 'Movies, shows and trends', added: 'the built-in culture pulse server', next: 'Turn on its switches below.' },
}

/** One Add menu (Iris): the built-in services not added yet, the keyless hosted searches, and any other MCP server.
 * Adding connects and lists its tools; nothing is looked up until approved. */
function AddLookup({ data, refresh, setResult, onOther }: { data: Overview; refresh: () => Promise<unknown>; setResult: (result: Result) => void; onOther: () => void }) {
  const [busy, setBusy] = useState(false)
  const add = async (path: string, body: object, label: string, next: string) => {
    if (busy) return
    setBusy(true)
    try {
      const created = await api<ContextServiceInfo>(path, body)
      const checked = await api<ContextServiceInfo>(`/context/services/${created.id}/check`, {})
      setResult(checked.check_error ? { tone: 'error', text: `Added ${label}, but the check failed: ${checked.check_error}` } : { tone: 'info', text: `Added ${label}. ${next}` })
      await refresh()
    } catch (error) { setResult({ tone: 'error', text: failure(error, 'Not added.') }) } finally { setBusy(false) }
  }
  const builtins = (['weather', 'pulse', 'culture'] as const).filter((kind) => !data.services.some((service) => service.builtin === kind))
    .map((kind): MenuItem => ({ label: BUILTINS[kind].label, value: 'built in', disabled: busy,
      onSelect: () => void add('/context/services/builtin', { kind }, BUILTINS[kind].added, BUILTINS[kind].next) }))
  const searches = SEARCH_PRESETS.filter((preset) => !data.services.some((service) => service.url === preset.url))
    .map((preset): MenuItem => ({ label: preset.name, value: 'web search', disabled: busy,
      onSelect: () => void add('/context/services/preset', { preset: preset.id }, preset.name, 'Review and turn on its web search or link reading below.') }))
  const items: MenuEntry[] = [...builtins, ...(builtins.length && searches.length ? ['separator' as const] : []), ...searches, 'separator', { label: 'Another MCP server…', onSelect: onOther }]
  return <Menu label="Add a lookup" icon={Plus} items={items} className="add-menu" />
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
  return <SwitchRow label="Open links I paste" checked={data.location.read_links} onChange={(value) => void save(value)}
    tip={`So ${name} can talk about them. This computer opens the page, like your browser would; Reddit and X posts are read through their public embeds. A link to your own computer or home network is never opened.`} />
}

/** Saves where you are, keeping what the call leaves out as it was. */
function useLocation(data: Overview, setResult: (result: Result) => void) {
  const client = useQueryClient()
  return async (change: Partial<{ user_place: string; user_latitude: number | null; user_longitude: number | null }>, done: string) => {
    const { user_place, user_latitude, user_longitude } = data.location
    try {
      await api('/context/location', { user_place, user_latitude, user_longitude, ...change }, 'PUT')
      setResult({ tone: 'info', text: done })
      await client.invalidateQueries({ queryKey: CONTEXT_KEY })
      return true
    } catch (error) { setResult({ tone: 'error', text: failure(error, 'Location not saved.') }); return false }
  }
}

/** Your city, saved when you leave the box or press Enter. */
function PlaceRow({ data, setResult }: { data: Overview; setResult: (result: Result) => void }) {
  const save = useLocation(data, setResult)
  const [place, setPlace] = useState(data.location.user_place)
  const commit = () => { if (place.trim() !== data.location.user_place.trim()) void save({ user_place: place.trim() }, 'Location saved.') }
  return (
    <SettingRow label="Your city" tip="Where you are, for weather and events near you. It is separate from where your companion lives, and is never detected automatically.">
      {(id) => <input id={id} value={place} maxLength={120} autoComplete="off" placeholder="Baltimore, MD" onChange={(event) => setPlace(event.target.value)}
        onBlur={commit} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); commit() } }} />}
    </SettingRow>
  )
}

/** Latitude and longitude, only for services that need them, behind one fold row that shows them. */
function Coordinates({ data, setResult }: { data: Overview; setResult: (result: Result) => void }) {
  const save = useLocation(data, setResult)
  const { user_latitude: lat, user_longitude: lon } = data.location
  const shown = lat === null || lon === null ? 'Not set' : `${lat}, ${lon}`
  return (
    <FoldRow summary="Exact coordinates" value={shown}>
      <CoordinateRow label="Latitude" tip="Decimal degrees, such as 39.29. North is positive. Only for services that need coordinates." saved={lat} save={(value) => save({ user_latitude: value }, 'Location saved.')} />
      <CoordinateRow label="Longitude" tip="Decimal degrees, such as -76.61. West is negative." saved={lon} save={(value) => save({ user_longitude: value }, 'Location saved.')} />
    </FoldRow>
  )
}

function CoordinateRow({ label, tip, saved, save }: { label: string; tip: string; saved: number | null; save: (value: number | null) => Promise<boolean> }) {
  const [text, setText] = useState(saved === null ? '' : String(saved))
  const commit = () => {
    const value = text.trim() === '' ? null : Number(text)
    if (value !== saved) void save(value)
  }
  return (
    <SettingRow nested label={label} tip={tip}>
      {(id) => <input id={id} inputMode="decimal" value={text} autoComplete="off" placeholder="Not set" onChange={(event) => setText(event.target.value)}
        onBlur={commit} onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); commit() } }} />}
    </SettingRow>
  )
}

/** A built-in server's sources in a few words for its row (Iris), and in full behind its "?". */
const BUILTIN_SHORT = {
  weather: 'Open-Meteo, NWS backup in the US',
  pulse: 'Google News, Wikipedia, ESPN and more',
  culture: 'Google News, iTunes, TVmaze and more',
}

const BUILTIN_SOURCES = {
  weather: 'Ships with the app; asks Open-Meteo, or the National Weather Service for US places when Open-Meteo fails',
  pulse: 'Ships with the app; asks Google News, Wikipedia, Reddit, ESPN, MLB and Open-Meteo',
  culture: 'Ships with the app; asks Google News, iTunes, Apple Music, TVmaze, Steam, Open Library, Google Trends, Wikipedia and Reddit',
}

function serviceWhere(service: ContextServiceInfo) {
  const where = service.builtin ? BUILTIN_SHORT[service.builtin]
    : service.transport === 'http' ? service.url : (service.command ?? []).join(' ')
  const server = service.server_info ? `${service.server_info.name} · MCP ${service.server_info.protocol}` : ''
  return [where, service.has_key ? 'key saved' : '', server].filter(Boolean).join(' · ')
}

/** What kind of service it is, and whether any of its lookups is on. */
function ServiceChips({ service }: { service: ContextServiceInfo }) {
  const on = service.mappings.some((mapping) => mapping.enabled && mapping.approved)
  return <span className="backend-chips">
    {service.check_error && <span className="badge badge-warn">Needs a look</span>}
    <span className="badge badge-quiet">{service.builtin ? 'Built in' : service.transport === 'http' ? 'HTTP' : 'Local program'}</span>
    <span className={on ? 'badge' : 'badge badge-quiet'}>{on ? 'On' : 'Off'}</span>
  </span>
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
      <FoldRow summary={service.name} sub={serviceWhere(service)} value={<ServiceChips service={service} />}>
      {service.check_error && <Notice tone="error">{service.check_error}</Notice>}
      <ServiceSwitches service={service} data={data} busy={busy} setBusy={setBusy} setResult={setResult} refresh={refresh} check={() => void check()} />
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
        <button type="button" className="text-button danger-text" aria-disabled={busy} onClick={() => void remove()}><Trash2 aria-hidden="true" />Remove</button>
      </div>
      </FoldRow>
    </li>
  )
}

interface SwitchesProps { service: ContextServiceInfo; data: Overview; busy: boolean; setBusy: (busy: boolean) => void; setResult: (result: Result) => void; refresh: () => Promise<unknown>; check: () => void }

/** The top of a lookup's fold (Iris): its own On switch, as a picture model has, and the state of its tools with Check beside it. */
function ServiceSwitches({ service, data, busy, setBusy, setResult, refresh, check }: SwitchesProps) {
  const on = serviceIsOn(service)
  const change = async (value: boolean) => {
    if (busy) return
    setBusy(true)
    try { await setServiceOn(service, value, data.categories); await refresh() } catch (error) { setResult({ tone: 'error', text: failure(error, 'Not saved.') }) } finally { setBusy(false) }
  }
  const sources = service.builtin ? `${BUILTIN_SOURCES[service.builtin]}. ` : ''
  const tip = canTurnOn(service) ? `${sources}Turning it on confirms what each lookup below sends; you can switch any of them off on its own.`
    : `${sources}Check it and set up a lookup below first.`
  const tools = service.checked_at ? countText(service.tools.length, 'tool found', 'tools found', 'No tools found') : 'Not checked yet'
  return <>
    <SwitchRow label="On" checked={on} disabled={!on && !canTurnOn(service)} tip={tip} onChange={(value) => void change(value)} />
    <SettingRow label="Tools" tip="Checking connects and lists its tools; it looks nothing up.">
      {() => <span className="row-control"><span className="row-value">{tools}</span>
        <button type="button" className="text-button" aria-disabled={busy} onClick={check}>{service.checked_at ? 'Check again' : 'Check'}</button></span>}
    </SettingRow>
  </>
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
      {on ? <p className="subtle">Sends {mapping.disclosure.sends.map((item) => propertyLabel(item.argument).toLowerCase()).join(', ') || 'nothing'} to “{mapping.tool}”.</p>
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
  const toolNamed = (name: string) => service.tools.find((item) => item.name === name)
  const [draft, setDraft] = useState(() => withAppFilled(initial, toolNamed(initial.tool)))
  const tool = toolNamed(draft.tool)
  const properties = Object.entries(tool?.input_schema.properties ?? {})
  const required = new Set(tool?.input_schema.required ?? [])
  const missing = missingArguments(tool, draft.arguments)
  return (
    <div className="context-mapping form-stack">
      <strong>{CATEGORY_LABELS[category]}</strong>
      <Field label="Tool" hint="Which of this service's tools runs for this lookup. What it does is described below.">{(id, hint) => (
        <select id={id} aria-describedby={hint} value={draft.tool} onChange={(event) => setDraft(withAppFilled({ tool: event.target.value, arguments: {}, run_in: draft.run_in }, toolNamed(event.target.value)))}>
          {service.tools.map((item) => <option key={item.name} value={item.name}>{`${propertyLabel(item.name)} (${item.name})`}</option>)}
        </select>
      )}</Field>
      <p className="subtle">{tool?.description || (properties.length ? '' : 'This tool takes no arguments.')}</p>
      {properties.map(([property, schema]) => (
        <ArgumentRow key={property} category={category} property={property} schema={schema} required={required.has(property)}
          argument={draft.arguments[property]} onSource={(source) => setDraft(withSource(draft, property, source))}
          onValue={(value) => setDraft({ ...draft, arguments: { ...draft.arguments, [property]: { source: 'literal', value } } })} />
      ))}
      {data.categories[category].purposes.map((purpose) => (
        <Toggle key={purpose} label={purposeLabel(category, purpose, name)}
          hint={canTry(category) ? data.purposes[purpose] : undefined} checked={draft.run_in.includes(purpose)} onChange={(value) => setDraft(withPurpose(draft, purpose, value))} />
      ))}
      {missing.length > 0 && <p className="subtle">The tool needs {missing.map((item) => propertyLabel(item).toLowerCase()).join(', ')}.</p>}
      <p className="subtle">Saving keeps it off. You will see exactly what it sends before turning it on.</p>
      <div className="form-actions">
        <button type="button" className="button primary" disabled={busy || !canSave(draft, tool)} onClick={() => onSave(draft)}>Save</button>
        <button type="button" className="button" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  )
}

interface ArgumentProps { category: ContextCategory; property: string; schema: ToolProperty; required: boolean; argument?: ToolArgument; onSource: (source: ArgumentSource | '') => void; onValue: (value: string | number | boolean) => void }

/** One argument of the tool, offered the way its schema types it. The app fills ids like session_id itself, so they are not shown. */
function ArgumentRow(props: ArgumentProps) {
  const kind = argumentKind(props.property, props.schema)
  if (kind === 'app') return null
  const label = props.required ? `${propertyLabel(props.property)} (required)` : propertyLabel(props.property)
  if (kind === 'boolean' || kind === 'choice') return <PickRow {...props} label={label} options={kind === 'boolean' ? [true, false] : props.schema.enum!} />
  if (kind === 'number') return <NumberRow {...props} label={label} />
  return <SourceRow {...props} label={label} />
}

type RowProps = ArgumentProps & { label: string }
const fixedValue = (argument?: ToolArgument) => argument?.source === 'literal' ? argument.value : undefined

/** Help the service wrote into its own schema, marked as quoted so it does not read as the app's copy. */
function serviceHint(description?: string, own?: string): ReactNode {
  if (!description && !own) return undefined
  return <>{description && <span className="service-hint"><span className="service-hint-from">From the service:</span> {description}</span>}{description && own ? ' ' : ''}{own}</>
}

/** A yes/no, or one of the tool's own listed values; left alone, the service uses its default. */
function PickRow({ schema, required, argument, label, options, onSource, onValue }: RowProps & { options: unknown[] }) {
  const name = useId()
  const fixed = fixedValue(argument)
  const current = fixed === undefined ? '' : String(options.findIndex((option) => option === fixed))
  const choose = (value: string) => value === '' ? onSource('') : onValue(options[Number(value)] as string | number | boolean)
  const choices = [{ value: '', label: required ? 'Choose one' : 'Default' },
    ...options.map((option, index) => ({ value: String(index), label: option === true ? 'Yes' : option === false ? 'No' : propertyLabel(String(option)) }))]
  if (choices.length > 5) {
    return (
      <Field label={label} hint={serviceHint(schema.description)}>{(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} value={current} onChange={(event) => choose(event.target.value)}>
          {choices.map((choice) => <option key={choice.value} value={choice.value}>{choice.value === '' && !required ? "The service's default" : choice.label}</option>)}
        </select>
      )}</Field>
    )
  }
  return (
    <fieldset className="argument-choice" aria-describedby={schema.description ? `${name}-hint` : undefined}>
      <legend className="field-label">{label}</legend>
      <div className="segmented">
        {choices.filter((choice) => !(required && choice.value === '')).map((choice) => (
          <label key={choice.value}>
            <input type="radio" className="visually-hidden" name={name} value={choice.value} checked={current === choice.value} onChange={() => choose(choice.value)} />
            <span>{choice.label}</span>
          </label>
        ))}
      </div>
      {schema.description && <small id={`${name}-hint`}>{serviceHint(schema.description)}</small>}
    </fieldset>
  )
}

/** A bounded number is a stepper that starts at "Default"; without bounds, a number box left empty for the default. */
function NumberRow({ schema, required, argument, label, onSource, onValue }: RowProps) {
  const fixed = fixedValue(argument)
  const set = (value: number | undefined) => value === undefined ? onSource('') : onValue(value)
  if (schema.minimum !== undefined && schema.maximum !== undefined) {
    return <OptionalStepper label={label} value={typeof fixed === 'number' ? fixed : undefined} min={schema.minimum} max={schema.maximum}
      hint={serviceHint(schema.description)} format={String} onChange={set} />
  }
  return <TextInput label={label} type="number" value={fixed === undefined ? '' : String(fixed)} min={schema.minimum} max={schema.maximum}
    hint={serviceHint(schema.description, required ? undefined : "Leave empty for the service's default.")} onChange={(value) => set(value === '' ? undefined : Number(value))} />
}

/** Text that can come from what you asked (or the link, or where you are), or a fixed value. */
function SourceRow({ category, schema, argument, label, onSource, onValue }: RowProps) {
  return (
    <div className="form-grid">
      <Field label={label} hint={serviceHint(schema.description)}>{(id, describedBy) => (
        <select id={id} aria-describedby={describedBy} value={argument?.source ?? ''} onChange={(event) => onSource(event.target.value as ArgumentSource | '')}>
          <option value="">Not sent</option>
          {sourcesFor(category).map((source) => <option key={source} value={source}>{SOURCE_LABELS[source]}</option>)}
        </select>
      )}</Field>
      {argument?.source === 'literal' && <TextInput label="Value" value={String(argument.value ?? '')} maxLength={200} onChange={onValue} hint="Sent exactly as written every time." />}
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
      <TextInput label="Name" value={draft.name} required maxLength={80} placeholder="Weather" onChange={(name) => set({ name })} hint="Your name for it, shown in this list." />
      <Field label="How it runs" hint="The service's instructions say which one it is." tip="An MCP service either runs as a program on this computer (stdio) or answers at a web address (streamable HTTP).">{(id, hint) => (
        <select id={id} aria-describedby={hint} value={draft.transport} onChange={(event) => set({ transport: event.target.value as ServiceDraft['transport'] })}>
          <option value="stdio">A program on this computer (stdio)</option>
          <option value="http">A server address (streamable HTTP)</option>
        </select>
      )}</Field>
      {draft.transport === 'stdio' ? <>
        <TextInput label="Program" value={draft.program} required maxLength={1000} placeholder="C:\Tools\weather-mcp.exe" onChange={(program) => set({ program })}
          hint="The app starts it only to check it or look something up, with a short time limit." />
        <TextArea label="Arguments, one per line" value={draft.args} rows={2} onChange={(args) => set({ args })} hint="Anything the program needs after its name, such as --stdio. Leave empty if it needs nothing." />
      </> : (
        <TextInput label="Server address" value={draft.url} required maxLength={2000} placeholder="https://example.com/mcp" onChange={(url) => set({ url })}
          hint="HTTPS, or HTTP for a server on this computer." />
      )}
      <div className="form-grid">
        <TextInput label="Key (optional)" type="password" value={draft.secret} maxLength={4000} onChange={(secret) => set({ secret })} hint="Kept in your system's credential store and sent only to this service." />
        <TextInput label={draft.transport === 'stdio' ? 'Environment variable for the key' : 'Header for the key'} value={draft.secretName} maxLength={100}
          placeholder={draft.transport === 'stdio' ? 'API_KEY' : 'Authorization'} onChange={(secretName) => set({ secretName })}
          hint={draft.transport === 'stdio' ? 'The name the program reads its key from. Its instructions say which.' : 'The header the server reads its key from. Its instructions say which.'} />
      </div>
      <div className="form-actions">
        <button type="submit" className="button primary" disabled={busy}>Add and check</button>
        <button type="button" className="button" onClick={onDone}>Cancel</button>
      </div>
    </form>
  )
}
