import type { BackendFiles, FileListKey, ModelFileKey, ModelFiles, ModelLink, SamplerSettings, StyleLora } from '../../types'

export interface FileSlot { key: ModelFileKey; label: string; role: ModelLink['role'] | null; hint: string; tip?: string }

/** The built-in ComfyUI workflow's loader inputs the user can choose files for, in the order shown. */
export const FILE_SLOTS: FileSlot[] = [
  { key: 'unet_name', label: 'Model', role: 'model', hint: 'From ComfyUI\'s models/diffusion_models folder.', tip: 'The image model the UNETLoader node loads. A Krea 2 Turbo file or a fine-tune of it; the workflow runs 8 steps at CFG 1, which suits Turbo.' },
  { key: 'clip_name', label: 'Text encoder', role: 'clip', hint: 'From models/text_encoders.', tip: 'Turns the prompt into what the model reads. Krea 2 uses the Qwen3-VL 4B encoder.' },
  { key: 'clip_type', label: 'Text encoder type', role: null, hint: 'krea2 for Krea 2 models.' },
  { key: 'vae_name', label: 'VAE', role: 'vae', hint: 'From models/vae.', tip: 'Turns the finished picture from the model\'s internal form into pixels. Krea 2 uses the Qwen Image VAE.' },
]

export const MISSING = ' (not on this server)'
export const NO_CHOICE: ModelFiles = { unet_name: '', clip_name: '', clip_type: '', vae_name: '' }
const NO_FILES: BackendFiles['options'] = { unet_name: [], clip_name: [], clip_type: [], vae_name: [], lora: [], sampler_name: [], scheduler: [] }
export const MAX_STYLE_LORAS = 3
export const NEW_STYLE_LORA: StyleLora = { name: '', strength: 0.7, trigger: '' }

/** What the server said, ready to show: its lists only when it answered, and the reason when it could not
 * be asked (`failed`, a request error). Until the app answers, the saved choice stands in for the defaults. */
export function serverFiles(data: BackendFiles | undefined, failed: string | null, saved: ModelFiles) {
  return {
    answered: Boolean(data) || failed !== null,
    defaults: data?.defaults ?? saved,
    options: data?.ok ? data.options : NO_FILES,
    krea: data?.ok ? data.krea : NO_FILES,
    error: data && !data.ok ? data.error : failed,
  }
}

/** The choices for one slot: the server's files (only Krea 2's when `kreaOnly` and it has any), with the
 * current value first when the list leaves it out. */
export function fileChoices(options: string[], current: string, krea: string[] = [], kreaOnly = false): { value: string; label: string }[] {
  const shown = kreaOnly && krea.length > 0 ? krea : options
  const listed = shown.map(value => ({ value, label: value }))
  if (!current || shown.includes(current)) return listed
  return [{ value: current, label: options.includes(current) ? current : current + MISSING }, ...listed]
}

/** Whether the server listed any Krea 2 file, so "Only Krea 2 files" has something to narrow to. */
export const hasKrea = (krea: Record<FileListKey, string[]>) => Object.values(krea).some(list => list.length > 0)

/** The request body for the style LoRAs: rows without a file are dropped, trigger words trimmed. */
export const stylesBody = (rows: StyleLora[]): { style_loras: StyleLora[] } =>
  ({ style_loras: rows.filter(row => row.name.trim()).slice(0, MAX_STYLE_LORAS).map(row => ({ name: row.name.trim(), strength: row.strength, trigger: row.trigger.trim() })) })

/** What each slot shows: the draft, else the saved choice, else the workflow's default file. */
export const shownFiles = (draft: Partial<ModelFiles>, saved: ModelFiles, defaults: ModelFiles): ModelFiles =>
  Object.fromEntries(FILE_SLOTS.map(({ key }) => [key, draft[key] ?? (saved[key] || defaults[key])])) as ModelFiles

/** The request body for saving: a slot set to its default is saved empty, so it follows the default. */
export const filesBody = (shown: ModelFiles, defaults: ModelFiles): ModelFiles =>
  Object.fromEntries(FILE_SLOTS.map(({ key }) => [key, shown[key].trim() === defaults[key] ? '' : shown[key].trim()])) as ModelFiles

export const isChosen = (saved: ModelFiles) => FILE_SLOTS.some(({ key }) => saved[key])

/** Download pages for the slots that have them, in slot order. */
export const linksByRole = (links: ModelLink[]) =>
  FILE_SLOTS.filter(slot => slot.role).map(slot => ({ slot, links: links.filter(link => link.role === slot.role) })).filter(group => group.links.length > 0)

/** Krea 2 Turbo's settings, the built-in workflow's own, shown until the server says otherwise. */
export const TURBO: SamplerSettings = { steps: 8, cfg: 1, sampler_name: 'euler', scheduler: 'simple' }
type Sampler = { steps: number; cfg: number; sampler_name: string; scheduler: string }

/** What each sampler field shows: the draft, else the saved value, else the workflow's own. */
export const shownSampler = (draft: Partial<SamplerSettings>, saved: SamplerSettings, defaults: SamplerSettings): Sampler =>
  Object.fromEntries((Object.keys(TURBO) as (keyof SamplerSettings)[]).map(key =>
    [key, draft[key] ?? saved[key] ?? defaults[key] ?? TURBO[key]])) as Sampler

export const isTuned = (saved: SamplerSettings) => Object.values(saved).some(value => value !== null)
