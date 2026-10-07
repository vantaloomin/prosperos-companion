import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import { FILE_SLOTS, MISSING, fileChoices, filesBody, TURBO, hasKrea, isChosen, isTuned, linksByRole, serverFiles, shownFiles, shownSampler, stylesBody } from '../../src/features/settings/modelFiles.ts'
import type { ModelFiles, ModelLink } from '../../src/types.ts'

const DEFAULTS: ModelFiles = { unet_name: 'krea2_turbo_fp8_scaled.safetensors', clip_name: 'qwen3vl_4b_fp8_scaled.safetensors', clip_type: 'krea2', vae_name: 'qwen_image_vae.safetensors' }
const NONE: ModelFiles = { unet_name: '', clip_name: '', clip_type: '', vae_name: '' }
// As a Windows ComfyUI lists them: subfolder, backslash and spaces kept.
const MUSE = 'Krea 2\\Muse by Stable Yogi Krea2 V3.5 Civ NVFP4 C84.safetensors'

test('each dropdown preselects the saved choice, else the default, and keeps a value the server lacks', () => {
  assert.deepEqual(shownFiles({}, NONE, DEFAULTS), DEFAULTS)
  assert.equal(shownFiles({}, { ...NONE, unet_name: MUSE }, DEFAULTS).unet_name, MUSE)
  assert.equal(shownFiles({ vae_name: 'Qwen\\sharp.safetensors' }, NONE, DEFAULTS).vae_name, 'Qwen\\sharp.safetensors')
  assert.deepEqual(fileChoices([MUSE], MUSE), [{ value: MUSE, label: MUSE }])
  assert.deepEqual(fileChoices([MUSE], DEFAULTS.unet_name), [{ value: DEFAULTS.unet_name, label: DEFAULTS.unet_name + MISSING }, { value: MUSE, label: MUSE }])
})

test('saving stores only what differs from the default, exactly as named', () => {
  assert.deepEqual(filesBody({ ...DEFAULTS, unet_name: MUSE }, DEFAULTS), { ...NONE, unet_name: MUSE })
  assert.deepEqual(filesBody(DEFAULTS, DEFAULTS), NONE)
  assert.ok(isChosen({ ...NONE, clip_type: 'qwen_image' }) && !isChosen(NONE))
})

test('download pages are grouped under the dropdown they fill', () => {
  const link = (role: ModelLink['role'], name: string): ModelLink => ({ role, name, url: `https://huggingface.co/${name}`, file: null, licence: 'Apache 2.0' })
  const groups = linksByRole([link('vae', 'v'), link('model', 'm1'), link('model', 'm2')])
  assert.deepEqual(groups.map(group => [group.slot.label, group.links.map(item => item.name)]), [['Model', ['m1', 'm2']], ['VAE', ['v']]])
  assert.deepEqual(FILE_SLOTS.map(slot => slot.label), ['Model', 'Text encoder', 'Text encoder type', 'VAE'])
})

test('the shipped download list links to pages, never to a file download', () => {
  const links = JSON.parse(readFileSync('companion/images/model_links.json', 'utf8')) as ModelLink[]
  assert.ok(links.length > 0)
  for (const item of links) {
    assert.match(item.url, /^https:\/\/huggingface\.co\/[\w.-]+\/[\w.-]+(\/tree\/main(\/[\w./-]+)?)?$/)
    assert.ok(['model', 'clip', 'vae'].includes(item.role) && item.name && item.licence)
  }
})

test('a server that cannot be asked leaves typed names, and one that answers fills the lists', () => {
  const options = { unet_name: [MUSE], clip_name: [], clip_type: ['krea2'], vae_name: [], lora: [], sampler_name: [], scheduler: [] }
  const krea = { unet_name: [MUSE], clip_name: [], clip_type: [], vae_name: [], lora: [], sampler_name: [], scheduler: [] }
  assert.deepEqual(serverFiles(undefined, null, NONE), { answered: false, defaults: NONE, options: { ...options, unet_name: [], clip_type: [] }, krea: { ...options, unet_name: [], clip_type: [] }, error: null })
  const down = serverFiles({ ok: false, error: 'Cannot reach the ComfyUI server.', defaults: DEFAULTS, sampler_defaults: TURBO, options, krea, character_lora: null }, null, NONE)
  assert.ok(down.answered && down.options.unet_name.length === 0 && down.defaults === DEFAULTS && down.error?.startsWith('Cannot reach'))
  assert.deepEqual(serverFiles({ ok: true, error: null, defaults: DEFAULTS, sampler_defaults: TURBO, options, krea, character_lora: null }, null, NONE).options, options)
  assert.equal(serverFiles(undefined, 'Not found.', NONE).error, 'Not found.')
})

test('the settings page opens download pages in a new tab', () => {
  const source = readFileSync('src/features/settings/ImageSettings.tsx', 'utf8')
  assert.match(source, /href=\{link\.url\} target="_blank" rel="noreferrer"/)
})

test('"Only Krea 2 files" narrows a list to its Krea 2 files but never drops the current choice', () => {
  const other = 'sdxl\\juggernaut.safetensors'
  assert.deepEqual(fileChoices([MUSE, other], '', [MUSE], true).map(choice => choice.value), [MUSE])
  assert.deepEqual(fileChoices([MUSE, other], other, [MUSE], true), [{ value: other, label: other }, { value: MUSE, label: MUSE }])
  assert.deepEqual(fileChoices([MUSE, other], '', [], true).map(choice => choice.value), [MUSE, other])
  assert.ok(hasKrea({ unet_name: [], clip_name: [], clip_type: [], vae_name: [], lora: ['a'], sampler_name: [], scheduler: [] }))
})

test('style LoRAs are saved without empty rows, trimmed, at most three', () => {
  const row = { name: ' Krea 2\\phone_photography_2025_krea2.safetensors ', strength: 0.7, trigger: ' phone photo ' }
  assert.deepEqual(stylesBody([row, { name: '', strength: 1, trigger: '' }, row, row, row]).style_loras,
    Array(3).fill({ name: 'Krea 2\\phone_photography_2025_krea2.safetensors', strength: 0.7, trigger: 'phone photo' }))
})

test('sampling starts on Krea 2 Turbo settings and shows a draft over a saved value', () => {
  const none = { steps: null, cfg: null, sampler_name: null, scheduler: null }
  assert.deepEqual(shownSampler({}, none, TURBO), { steps: 8, cfg: 1, sampler_name: 'euler', scheduler: 'simple' })
  assert.deepEqual(shownSampler({ steps: 12 }, { ...none, scheduler: 'beta' }, TURBO), { steps: 12, cfg: 1, sampler_name: 'euler', scheduler: 'beta' })
  assert.ok(isTuned({ ...none, cfg: 2 }) && !isTuned(none))
})
