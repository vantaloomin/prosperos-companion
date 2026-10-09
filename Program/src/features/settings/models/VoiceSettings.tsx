import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, Play } from 'lucide-react'
import { api, ApiError } from '../../../api'
import { Notice } from '../../../components/Feedback'
import { Field, TextInput, Toggle } from '../../../components/Fields'

type Engine = 'builtin' | 'openai' | 'elevenlabs' | 'google'
type Hosted = Exclude<Engine, 'builtin'>
interface VoiceView {
  voice_notes: boolean
  engine: Engine
  daily_limit: number
  ready: boolean
  /** Where each hosted engine's key comes from, or null without one. Keys themselves never come back. */
  keys: Record<Hosted, 'saved' | 'profile' | 'environment' | null>
  builtin: { ready: boolean; available: boolean; download_mb: number | null; downloading: boolean; error: string }
}
interface VoiceOption { id: string; label: string }
interface CompanionVoice { id: string; name: string; voice: string; chosen_by: 'app' | 'user' }
interface CompanionVoices { engine: Engine; voices: VoiceOption[]; companions: CompanionVoice[]; message: string }

const KEY = ['voice']
const ENGINES: Record<Engine, string> = { builtin: 'Built-in voice (Kokoro, on this PC)', openai: 'OpenAI', elevenlabs: 'ElevenLabs', google: 'Google Cloud' }
const KEY_HINTS: Record<Hosted, string> = {
  openai: 'From platform.openai.com. Without one here, a key saved for an OpenAI text model is used.',
  elevenlabs: 'From elevenlabs.io, under your profile > API keys.',
  google: 'A Google Cloud API key with the Text-to-Speech API turned on.',
}
const SOURCES = { saved: 'A key is saved.', profile: 'Using the key from your OpenAI text model.', environment: 'Using the key from the environment.' }
const failure = (error: unknown) => error instanceof Error ? error.message : 'That did not work.'

/** Plays a short sample of a companion's voice; the sample is made now and not kept. */
async function playPreview(companionId: string, engine: Engine, voice: string) {
  const response = await fetch('/api/voice/preview', {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Companion-Client': 'workspace' },
    body: JSON.stringify({ companion_id: companionId, engine, voice }),
  }).catch(() => { throw new ApiError('Cannot reach the Companion. Check that it is still running.', 0) })
  if (!response.ok) {
    const data = await response.json().catch(() => ({})) as { detail?: unknown }
    throw new ApiError(typeof data.detail === 'string' ? data.detail : `The preview did not play (error ${response.status}).`, response.status)
  }
  const url = URL.createObjectURL(await response.blob())
  const audio = new Audio(url)
  audio.onended = () => URL.revokeObjectURL(url)
  await audio.play()
}

/** Settings > Models: companions now and then send a short voice note instead of a text (companion/voice/). */
export function VoiceSettings() {
  const client = useQueryClient()
  const query = useQuery({ queryKey: KEY, queryFn: () => api<VoiceView>('/voice'), refetchInterval: (state) => state.state.data?.builtin.downloading ? 3000 : false })
  const [error, setError] = useState('')
  const data = query.data
  if (!data) return null
  const save = async (change: Partial<Pick<VoiceView, 'voice_notes' | 'engine' | 'daily_limit'>>) => {
    setError('')
    try { client.setQueryData(KEY, await api<VoiceView>('/voice', change, 'PUT')) } catch (failed) { setError(failure(failed)) }
  }
  return <section className="settings-section form-stack" aria-labelledby="voice-heading">
    <div>
      <h2 id="voice-heading">Voice notes</h2>
      <p className="subtle">Now and then a companion sends a short voice note instead of a text, a few a day at most, in a voice the app picks to suit them. The model writes the words as usual; a voice engine only reads them aloud.</p>
    </div>
    <Toggle label="Send voice notes now and then" checked={data.voice_notes} onChange={(on) => void save({ voice_notes: on })} hint={data.voice_notes && !data.ready ? 'Messages stay texts until the voice below is ready.' : undefined} />
    <Field label="Voice engine">{(id) => (
      <select id={id} value={data.engine} onChange={(event) => void save({ engine: event.target.value as Engine })}>
        {(Object.keys(ENGINES) as Engine[]).map((engine) => <option key={engine} value={engine}>{ENGINES[engine]}</option>)}
      </select>
    )}</Field>
    {data.engine === 'builtin' ? <BuiltinVoice view={data} onChange={(view) => client.setQueryData(KEY, view)} /> : <VoiceKey engine={data.engine} source={data.keys[data.engine]} onChange={(view) => { client.setQueryData(KEY, view); void client.invalidateQueries({ queryKey: ['voice-companions'] }) }} />}
    {error && <Notice tone="error">{error}</Notice>}
    <CompanionVoiceList engine={data.engine} ready={data.ready} />
  </section>
}

function BuiltinVoice({ view, onChange }: { view: VoiceView; onChange: (view: VoiceView) => void }) {
  const [error, setError] = useState('')
  const { builtin } = view
  const download = async () => {
    setError('')
    try { onChange(await api<VoiceView>('/voice/builtin/download', {})) } catch (failed) { setError(failure(failed)) }
  }
  if (builtin.ready) return <p className="subtle">The built-in voice is ready. It runs on this PC's processor, so notes take a few seconds to record and nothing leaves the PC.</p>
  if (!builtin.available) return <p className="subtle">There is no built-in voice download for this computer. Choose OpenAI, ElevenLabs or Google.</p>
  return <div className="form-stack">
    <div className="form-actions">
      <button type="button" className="button" onClick={() => void download()} disabled={builtin.downloading}><Download size={15} aria-hidden="true" />{builtin.downloading ? 'Downloading…' : `Download the built-in voice (${builtin.download_mb} MB)`}</button>
      <small>Kokoro and sherpa-onnx from sherpa-onnx's official releases, checked against pinned checksums. Apache 2.0. With background activity on, this downloads by itself.</small>
    </div>
    {(error || builtin.error) && <Notice tone="error">{error || builtin.error}</Notice>}
  </div>
}

function VoiceKey({ engine, source, onChange }: { engine: Hosted; source: VoiceView['keys'][Hosted]; onChange: (view: VoiceView) => void }) {
  const [key, setKey] = useState('')
  const [error, setError] = useState('')
  const save = async (value: string) => {
    setError('')
    try { onChange(await api<VoiceView>('/voice/key', { engine, api_key: value }, 'PUT')); setKey('') } catch (failed) { setError(failure(failed)) }
  }
  return <div className="form-stack">
    <TextInput label={`${ENGINES[engine]} API key`} type="password" value={key} onChange={setKey} maxLength={500} placeholder={source ? 'Saved' : ''} hint={source ? SOURCES[source] : KEY_HINTS[engine]} />
    <div className="form-actions">
      <button type="button" className="button" onClick={() => void save(key)} disabled={!key}>Save key</button>
      {source === 'saved' && <button type="button" className="text-button" onClick={() => void save('')}>Remove key</button>}
      <small>Only each note's words are sent to {ENGINES[engine]}, and it bills your account for them.</small>
    </div>
    {error && <Notice tone="error">{error}</Notice>}
  </div>
}

function CompanionVoiceList({ engine, ready }: { engine: Engine; ready: boolean }) {
  const client = useQueryClient()
  const query = useQuery({ queryKey: ['voice-companions', engine, ready], queryFn: () => api<CompanionVoices>(`/voice/companions?engine=${engine}`) })
  const [error, setError] = useState('')
  const data = query.data
  if (!data) return null
  if (data.message) return <p className="subtle">{data.message}</p>
  const choose = async (companion: CompanionVoice, voice: string) => {
    setError('')
    try { await api(`/voice/companions/${companion.id}`, { engine, voice }, 'PUT'); await client.invalidateQueries({ queryKey: ['voice-companions', engine] }) } catch (failed) { setError(failure(failed)) }
  }
  return <div className="form-stack">
    <h3>Voices</h3>
    <p className="subtle">The app picks each voice from their pronouns and where they live. Choose another if one does not sound right.</p>
    {data.companions.map((companion) => <CompanionVoiceRow key={companion.id} companion={companion} engine={engine} voices={data.voices} ready={ready} onChoose={(voice) => void choose(companion, voice)} onError={setError} />)}
    {error && <Notice tone="error">{error}</Notice>}
  </div>
}

interface RowProps { companion: CompanionVoice; engine: Engine; voices: VoiceOption[]; ready: boolean; onChoose: (voice: string) => void; onError: (message: string) => void }

function CompanionVoiceRow({ companion, engine, voices, ready, onChoose, onError }: RowProps) {
  const [playing, setPlaying] = useState(false)
  const preview = async () => {
    setPlaying(true); onError('')
    try { await playPreview(companion.id, engine, companion.voice) } catch (failed) { onError(failure(failed)) } finally { setPlaying(false) }
  }
  return <div className="form-actions">
    <Field label={companion.name} hint={companion.chosen_by === 'app' ? 'Picked by the app.' : 'Your choice.'}>{(id, hint) => (
      <select id={id} aria-describedby={hint} value={companion.chosen_by === 'app' ? '' : companion.voice} onChange={(event) => onChoose(event.target.value)}>
        <option value="">App's pick: {voices.find((voice) => voice.id === companion.voice)?.label ?? companion.voice}</option>
        {voices.map((voice) => <option key={voice.id} value={voice.id}>{voice.label}</option>)}
      </select>
    )}</Field>
    <button type="button" className="button" onClick={() => void preview()} disabled={!ready || playing}><Play size={15} aria-hidden="true" />{playing ? 'Recording…' : 'Preview'}</button>
  </div>
}
