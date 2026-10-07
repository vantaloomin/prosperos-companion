import type { BackendFiles, ModelFileKey, ModelFiles, ModelLink } from '../../types'

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
const NO_FILES: BackendFiles['options'] = { unet_name: [], clip_name: [], clip_type: [], vae_name: [] }

/** What the server said, ready to show: its lists only when it answered, and the reason when it could not
 * be asked (`failed`, a request error). Until the app answers, the saved choice stands in for the defaults. */
export function serverFiles(data: BackendFiles | undefined, failed: string | null, saved: ModelFiles) {
  return {
    answered: Boolean(data) || failed !== null,
    defaults: data?.defaults ?? saved,
    options: data?.ok ? data.options : NO_FILES,
    error: data && !data.ok ? data.error : failed,
  }
}

/** The choices for one slot: the server's files, with the current value first when the server does not list it. */
export function fileChoices(options: string[], current: string): { value: string; label: string }[] {
  const listed = options.map(value => ({ value, label: value }))
  return current && !options.includes(current) ? [{ value: current, label: current + MISSING }, ...listed] : listed
}

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
