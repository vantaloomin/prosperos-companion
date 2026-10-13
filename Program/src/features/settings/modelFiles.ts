import type { BackendFiles, FileListKey, ImageFamily, ModelFileKey, ModelFiles, ModelLink, SamplerSettings, StyleLora } from '../../types'

export interface FileSlot { key: ModelFileKey; label: string; role: ModelLink['role'] | null; hint: string; tip?: string }

/** A model family a ComfyUI server can run a built-in workflow for (companion/images/adapters/comfyui.py FAMILIES). */
export interface Family { label: string; short: string; sampling: string; reference: boolean; slots: FileSlot[] }

const separate = (model: string, encoder: string, type: string, vae: string): FileSlot[] => [
  { key: 'unet_name', label: 'Model', role: 'model', hint: 'From ComfyUI\'s models/diffusion_models folder.', tip: model },
  { key: 'clip_name', label: 'Text encoder', role: 'clip', hint: 'From models/text_encoders.', tip: encoder },
  { key: 'clip_type', label: 'Text encoder type', role: null, hint: type },
  { key: 'vae_name', label: 'VAE', role: 'vae', hint: 'From models/vae.', tip: vae },
]

/** In the order the dropdown lists them; Krea 2 first and the default. */
export const FAMILIES: Record<ImageFamily, Family> = {
  krea2: {
    label: 'Krea 2', short: 'Krea 2', sampling: 'Krea 2 Turbo', reference: true,
    slots: separate('The image model the UNETLoader node loads. A Krea 2 Turbo file or a fine-tune of it; the workflow runs 8 steps at CFG 1, which suits Turbo.',
      'Turns the prompt into what the model reads. Krea 2 uses the Qwen3-VL 4B encoder.', 'krea2 for Krea 2 models.',
      'Turns the finished picture from the model\'s internal form into pixels. Krea 2 uses the Qwen Image VAE.'),
  },
  qwen21: {
    label: 'Qwen Image 2.1', short: 'Qwen Image 2.1', sampling: 'Qwen Image 2.1 Turbo', reference: true,
    slots: separate('A Qwen Image 2.1 file. The Turbo one suits the workflow\'s 8 steps at CFG 1; the full model wants about 25.',
      'Qwen Image 2.1 uses the Qwen3-VL 8B encoder.', 'qwen_image for Qwen Image models.', 'Qwen Image 2.1 has a VAE of its own.'),
  },
  zimage: {
    label: 'Z-Image Turbo', short: 'Z-Image', sampling: 'Z-Image Turbo', reference: false,
    slots: separate('A Z-Image Turbo file or a fine-tune of it; the workflow runs 8 steps at CFG 1.',
      'Z-Image uses the Qwen3 4B encoder.', 'lumina2 for Z-Image.', 'Z-Image uses the Flux VAE (ae.safetensors).'),
  },
  anima: {
    label: 'Anima', short: 'Anima', sampling: 'Anima Turbo', reference: false,
    slots: separate('An Anima file. Anima Turbo suits the workflow\'s 10 steps at CFG 1; Base and Aesthetic want 30 or more at CFG 4.',
      'Anima uses the small Qwen3 0.6B encoder.', 'stable_diffusion for Anima.', 'Anima uses the Qwen Image VAE, the same file as Krea 2.'),
  },
  booru: {
    label: 'Booru (SDXL, Pony, Illustrious)', short: 'SDXL', sampling: 'Illustrious XL', reference: false,
    slots: [{ key: 'ckpt_name', label: 'Model', role: 'model', hint: 'From ComfyUI\'s models/checkpoints folder.', tip: 'One file holds the model, its text encoders and VAE. Any SDXL, Pony or Illustrious checkpoint works.' }],
  },
}
export const FAMILY_KEYS = Object.keys(FAMILIES) as ImageFamily[]
export const familyOf = (family: ImageFamily | null | undefined): Family => FAMILIES[family ?? 'krea2'] ?? FAMILIES.krea2

export const MISSING = ' (not on this server)'
/** Every list empty, for the loaders a family does not have and a server that did not answer. */
const NO_FILES: Record<FileListKey, string[]> = { unet_name: [], clip_name: [], clip_type: [], vae_name: [], ckpt_name: [], lora: [], sampler_name: [], scheduler: [] }
export const MAX_STYLE_LORAS = 3
export const NEW_STYLE_LORA: StyleLora = { name: '', strength: 0.7, trigger: '' }

/** What the server said, ready to show: its lists only when it answered, and the reason when it could not
 * be asked (`failed`, a request error). Until the app answers, the saved choice stands in for the defaults. */
export function serverFiles(data: BackendFiles | undefined, failed: string | null, saved: ModelFiles) {
  return {
    answered: Boolean(data) || failed !== null,
    defaults: data?.defaults ?? saved,
    options: { ...NO_FILES, ...(data?.ok ? data.options : {}) } as Record<FileListKey, string[]>,
    matching: { ...NO_FILES, ...(data?.ok ? data.matching : {}) } as Record<FileListKey, string[]>,
    error: data && !data.ok ? data.error : failed,
  }
}

/** The choices for one slot: the server's files (only the family's when `familyOnly` and it has any), with the
 * current value first when the list leaves it out. */
export function fileChoices(options: string[], current: string, matching: string[] = [], familyOnly = false): { value: string; label: string }[] {
  const shown = familyOnly && matching.length > 0 ? matching : options
  const listed = shown.map(value => ({ value, label: value }))
  if (!current || shown.includes(current)) return listed
  return [{ value: current, label: options.includes(current) ? current : current + MISSING }, ...listed]
}

/** Whether the server listed any of the family's files, so "Only … files" has something to narrow to. */
export const hasMatching = (matching: Partial<Record<FileListKey, string[]>>) => Object.values(matching).some(list => (list ?? []).length > 0)

/** The request body for the style LoRAs: rows without a file are dropped, trigger words trimmed. */
export const stylesBody = (rows: StyleLora[]): { style_loras: StyleLora[] } =>
  ({ style_loras: rows.filter(row => row.name.trim()).slice(0, MAX_STYLE_LORAS).map(row => ({ name: row.name.trim(), strength: row.strength, trigger: row.trigger.trim() })) })

/** What each slot shows: the draft, else the saved choice, else the workflow's default file. */
export const shownFiles = (slots: FileSlot[], draft: ModelFiles, saved: ModelFiles, defaults: ModelFiles): ModelFiles =>
  Object.fromEntries(slots.map(({ key }) => [key, draft[key] ?? (saved[key] || defaults[key] || '')]))

/** The request body for saving: a slot set to its default is saved empty, so it follows the default. */
export const filesBody = (slots: FileSlot[], shown: ModelFiles, defaults: ModelFiles): ModelFiles =>
  Object.fromEntries(slots.map(({ key }) => [key, (shown[key] ?? '').trim() === defaults[key] ? '' : (shown[key] ?? '').trim()]))

/** Every slot back to its default. */
export const noChoice = (slots: FileSlot[]): ModelFiles => Object.fromEntries(slots.map(({ key }) => [key, '']))

export const isChosen = (saved: ModelFiles) => Object.values(saved).some(Boolean)

/** Download pages for the family's slots that have them, in slot order. */
export const linksByRole = (links: ModelLink[], family: ImageFamily = 'krea2') => {
  const own = links.filter(link => (link.family ?? 'krea2') === family)
  return [...familyOf(family).slots.filter(slot => slot.role), REFERENCE_SLOT].map(slot => ({ slot, links: own.filter(link => link.role === slot.role) })).filter(group => group.links.length > 0)
}

/** Files only the built-in reference workflow (profile pictures) uses; not a pickable slot. */
const REFERENCE_SLOT = { label: 'Pictures made from a reference', role: 'reference' }

/** Krea 2 Turbo's settings, the default family's own, shown until the server says otherwise. */
export const TURBO: SamplerSettings = { steps: 8, cfg: 1, sampler_name: 'euler', scheduler: 'simple' }
type Sampler = { steps: number; cfg: number; sampler_name: string; scheduler: string }

/** What each sampler field shows: the draft, else the saved value, else the workflow's own. */
export const shownSampler = (draft: Partial<SamplerSettings>, saved: SamplerSettings, defaults: SamplerSettings): Sampler =>
  Object.fromEntries((Object.keys(TURBO) as (keyof SamplerSettings)[]).map(key =>
    [key, draft[key] ?? saved[key] ?? defaults[key] ?? TURBO[key]])) as Sampler

export const isTuned = (saved: SamplerSettings) => Object.values(saved).some(value => value !== null)
