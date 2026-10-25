// Their look in chat (companion/their_look.py, Hit List #80): a companion's own colour and name font in their chat.
// The server sends ids only; the colours are worked out here against the chat's own background, so the name always
// reads at 4.5:1 or more in every scheme and chat style, a custom palette included (tests/ui/theirLook.test.ts).
import bank from '../../../companion/world/data/their_looks.json' with { type: 'json' }
import { contrast } from '../settings/palette.ts'

export type Mood = 'bright' | 'muted' | 'deep' | 'pale'
export interface TheirLook { family: string; font: string; shade: number; mood: Mood | null }
export interface LookView {
  level: number
  everywhere_off: boolean
  look: TheirLook | null
  picked: { family: string; font: string }
  own: { family: string | null; font: string | null }
  steady: boolean
  use_mine: boolean
  changes: { text: string; at: string }[]
}
/** The colours a chat's look sits on, read from the chat itself (its style may have its own, like Retro IM). */
export interface Ground { canvas: string; surface: string; raised: string; text: string; muted: string; retro: boolean }

export const THEIR_LOOK_KEY = ['their-look'] as const
export const FAMILIES: { id: string; label: string; hue: number; sat: number }[] = bank.families
export const FONTS: { id: string; label: string; family: string; weight: number }[] = bank.fonts
const NAME_MIN = 4.5
// Each everyday shade is how far it stands from the background: a season or birthday moves it between these.
const DRIFT = [6.2, 7, 5.5]
// Mood moves the saturation, a little of the hue (warmer toward orange, cooler toward blue) and how far it stands out.
const MOODS: Record<Mood, { sat: number; toward: number | null; target: number | null }> = {
  bright: { sat: 15, toward: 30, target: null }, muted: { sat: -25, toward: 215, target: null },
  deep: { sat: 10, toward: null, target: 5 }, pale: { sat: -28, toward: null, target: 8.5 },
}

function hsl(hue: number, sat: number, light: number) {
  const s = sat / 100, l = light / 100
  const chroma = (1 - Math.abs(2 * l - 1)) * s
  const part = (offset: number) => {
    const k = (offset + hue / 30) % 12
    return Math.round(255 * (l - chroma / 2 * Math.max(-1, Math.min(k - 3, 9 - k, 1))))
  }
  return '#' + [0, 8, 4].map((offset) => part(offset).toString(16).padStart(2, '0')).join('')
}
const channels = (hex: string) => [1, 3, 5].map((offset) => parseInt(hex.slice(offset, offset + 2), 16))
export function mix(left: string, right: string, weight: number) {
  const second = channels(right)
  return '#' + channels(left).map((value, index) => Math.round(value * (1 - weight) + second[index] * weight).toString(16).padStart(2, '0')).join('')
}
const lowest = (colour: string, grounds: string[]) => Math.min(...grounds.map((ground) => contrast(colour, ground)))
export const lightGround = (ground: Pick<Ground, 'canvas'>) => contrast(ground.canvas, '#000000') > contrast(ground.canvas, '#ffffff')

/** Turns a hue toward another by up to `step` degrees. */
function toward(hue: number, target: number, step: number) {
  const gap = ((target - hue + 540) % 360) - 180
  return (hue + Math.sign(gap) * Math.min(step, Math.abs(gap)) + 360) % 360
}

/** The lightness that stands `target` away from every ground, as near the ground as that allows: lighter on a dark
 * chat, darker on a light one. Where no lightness gets there (a mid-grey custom palette), the text colour. */
function standing(hue: number, sat: number, target: number, grounds: string[], light: boolean, text: string) {
  let low = light ? 2 : 40, high = light ? 60 : 98
  const reaches = (lightness: number) => lowest(hsl(hue, sat, lightness), grounds) >= target
  if (!reaches(light ? low : high)) return text
  for (let step = 0; step < 18; step++) {
    const middle = (low + high) / 2
    if (reaches(middle) === light) low = middle; else high = middle
  }
  return hsl(hue, sat, light ? low : high)
}

/** Their name's colour in this chat. */
export function nameColour(look: TheirLook, ground: Ground) {
  const family = FAMILIES.find((item) => item.id === look.family) ?? FAMILIES[0]
  const mood = look.mood ? MOODS[look.mood] : null
  const hue = mood?.toward != null ? toward(family.hue, mood.toward, 10) : family.hue
  const sat = Math.max(8, Math.min(90, family.sat + (mood?.sat ?? 0)))
  const target = mood?.target ?? DRIFT[look.shade] ?? DRIFT[0]
  return standing(hue, sat, target, namesSitOn(ground), lightGround(ground), ground.text)
}

/** Retro IM's names sit on its white (or dark) window; every other style's on the canvas, the surface and, in a
 * header tint, near them. */
const namesSitOn = (ground: Ground) => ground.retro ? [ground.canvas] : [ground.canvas, ground.surface]

/** The strongest tint of `base` toward `colour` (up to `most`) that keeps every one of `texts` readable on it. */
export function tint(base: string, colour: string, texts: string[], most: number) {
  for (const weight of [most, most * .75, most * .5, most * .25]) {
    const tinted = mix(base, colour, weight)
    if (texts.every((text) => contrast(text, tinted) >= NAME_MIN)) return tinted
  }
  return base
}

const inkOn = (colour: string) => contrast(colour, '#ffffff') > contrast(colour, '#000000') ? '#ffffff' : '#000000'

/** The CSS variables their chat gets: their name and accent, the header and bubble tints, the Visual novel plate and
 * their name font. */
export function lookStyles(look: TheirLook, ground: Ground): Record<string, string> {
  const name = nameColour(look, ground)
  const font = FONTS.find((item) => item.id === look.font) ?? FONTS[0]
  return {
    '--their-name': name, '--their-accent': name,
    '--their-header': tint(ground.canvas, name, [ground.text, ground.muted, name], .12),
    '--their-bubble': tint(ground.raised, name, [ground.text], .14),
    '--their-plate': name, '--their-on-plate': inkOn(name),
    '--their-font': font.family, '--their-weight': String(font.weight),
  }
}

/** Reads a chat's ground from the element its style sets colours on. */
export function groundOf(element: HTMLElement): Ground | null {
  const styles = getComputedStyle(element)
  const read = (name: string) => normalHex(styles.getPropertyValue(name).trim())
  const canvas = read('--canvas'), surface = read('--surface'), text = read('--text')
  if (!canvas || !surface || !text) return null
  return { canvas, surface, text, raised: read('--raised') ?? surface, muted: read('--muted') ?? text, retro: element.classList.contains('chat-retro') }
}

function normalHex(value: string) {
  if (/^#[\da-f]{6}$/i.test(value)) return value.toLowerCase()
  if (/^#[\da-f]{3}$/i.test(value)) return '#' + [...value.slice(1)].map((digit) => digit + digit).join('').toLowerCase()
  return null
}

export const familyLabel = (id: string) => FAMILIES.find((item) => item.id === id)?.label ?? id
export const fontLabel = (id: string) => FONTS.find((item) => item.id === id)?.label ?? id
