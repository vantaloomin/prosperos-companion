import { useState } from 'react'
import { Play } from 'lucide-react'
import { Notice } from '../../../components/Feedback'
import { TextInput, Toggle } from '../../../components/Fields'
import { shownPath } from '../../../paths'
import { usePhoneStatus } from '../../phone/phoneAccess'
import { STATE_TEXT, programFor, useLauncher, type LocalProgram } from './launcher'

const failure = (error: unknown) => error instanceof Error ? error.message : 'That did not work.'
const PLACEHOLDERS: Record<LocalProgram['program'], string> = {
  lmstudio: 'C:\\Users\\you\\.lmstudio\\bin\\lms.exe', ollama: 'C:\\Users\\you\\AppData\\Local\\Programs\\Ollama\\ollama.exe',
  kobold: 'C:\\koboldcpp\\koboldcpp.exe', comfyui: 'C:\\ComfyUI_windows_portable',
}

/** Settings > Models: start LM Studio, Ollama, KoboldCpp or ComfyUI from here, and optionally with the Companion. */
export function LocalPrograms() {
  const launcher = useLauncher()
  const [error, setError] = useState('')
  const data = launcher.query.data
  if (!data || data.programs.length === 0) return null
  const act = async (work: () => Promise<unknown>) => { setError(''); try { await work() } catch (failed) { setError(failure(failed)) } }
  const order = data.programs.map(item => item.label).join(', then ')
  return <section className="settings-section form-stack" aria-labelledby="local-programs-heading">
    <div>
      <h2 id="local-programs-heading">Local programs</h2>
      <p className="subtle">Start the programs your local models run in, with the address, model and context size set above. They keep running after the Companion closes.</p>
    </div>
    <ul className="model-profiles">
      {data.programs.map(item => <ProgramRow key={item.program} item={item} act={act} launcher={launcher} />)}
    </ul>
    {error && <Notice tone="error">{error}</Notice>}
    <Toggle label="Start these when the Companion starts" checked={data.auto_launch} onChange={(checked) => void act(() => launcher.setAuto(checked))}
      hint={`${order}, each once the one before answers. Off until you turn it on, since it opens other programs.`} />
  </section>
}

type Launcher = ReturnType<typeof useLauncher>

function ProgramRow({ item, act, launcher }: { item: LocalProgram; act: (work: () => Promise<unknown>) => Promise<void>; launcher: Launcher }) {
  const [editing, setEditing] = useState(false)
  const missing = !item.path
  const save = (body: { path: string; model_path?: string }) => act(async () => { await launcher.choose(item.program, body); setEditing(false) })
  return <li className="model-profile">
    <div>
      <h3>{item.label}</h3>
      <p className="subtle">For {item.used_by.map(use => use.name).join(', ')} · {item.address}</p>
      <p className="subtle" role="status">{STATE_TEXT[item.state]}{item.message ? ` ${item.message}` : ''}</p>
      {!editing && <p className="subtle">{whereText(item)}</p>}
      {(editing || missing || item.needs_model) && <WhereForm item={item} save={save} cancel={editing ? () => setEditing(false) : undefined} />}
    </div>
    <div className="form-actions">
      <LaunchButton item={item} onLaunch={() => void act(() => launcher.launch(item.program))} />
      {!editing && !missing && <button type="button" className="text-button" onClick={() => setEditing(true)}>Change where it is</button>}
    </div>
  </li>
}

function whereText(item: LocalProgram) {
  if (!item.path) return 'Not found on this PC.'
  return shownPath(item.path) + (item.model_path ? ` · ${shownPath(item.model_path)}` : '')
}

/** Where the program is, typed only when it was not found, and KoboldCpp's model file. */
function WhereForm({ item, save, cancel }: { item: LocalProgram; save: (body: { path: string; model_path?: string }) => void; cancel?: () => void }) {
  const [path, setPath] = useState(item.path)
  const [model, setModel] = useState(item.model_path)
  const kobold = item.program === 'kobold'
  return <div className="form-stack where-form">
    <TextInput label={item.program === 'comfyui' ? 'ComfyUI folder, app or launch script' : `Where ${item.label} is`} value={path} onChange={setPath} maxLength={1000} placeholder={PLACEHOLDERS[item.program]}
      hint={item.program === 'comfyui' ? 'A .bat, .cmd or .sh you start ComfyUI with runs as it is, with its own settings. Its port should match the address above.' : undefined} />
    {kobold && <TextInput label="Model file" value={model} onChange={setModel} maxLength={1000} placeholder="C:\Models\model.gguf" hint="The .gguf file KoboldCpp loads, or a .kcpps settings file." />}
    <div className="form-actions">
      <button type="button" className="button primary" onClick={() => save(kobold ? { path, model_path: model } : { path })}>Save</button>
      {cancel && <button type="button" className="button" onClick={cancel}>Cancel</button>}
    </div>
  </div>
}

function LaunchButton({ item, onLaunch }: { item: LocalProgram; onLaunch: () => void }) {
  const unavailable = item.state === 'running' || item.state === 'starting' || !item.path || item.needs_model
  return <button type="button" className="button" aria-disabled={unavailable} onClick={() => { if (!unavailable) onLaunch() }}>
    <Play size={15} aria-hidden="true" />{item.state === 'starting' ? 'Starting…' : item.state === 'running' ? `${item.label} is running` : `Launch ${item.label}`}
  </button>
}

/** A launch button beside a profile or image backend that runs in a program the Companion can start. */
export function LaunchFor({ id }: { id: string }) {
  // A phone never starts programs on the PC, so it does not ask.
  const launcher = useLauncher(usePhoneStatus().data?.remote === false)
  const item = programFor(launcher.query.data, id)
  // Not found or still missing its model file: Local programs below says what it needs.
  if (!item || item.state === 'running' || !item.path || item.needs_model) return null
  return <LaunchButton item={item} onLaunch={() => void launcher.launch(item.program).catch(() => undefined)} />
}
