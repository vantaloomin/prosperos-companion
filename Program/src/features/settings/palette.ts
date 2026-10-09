// Color schemes and the custom palette, from prosperos-study src/features/settings/palette.ts.

export interface Palette { accent: string; background: string; surface: string; text: string }
export const COLOR_SCHEMES = [
  { id: 'ink', label: 'Ink', swatch: '#191816' },
  { id: 'slate', label: 'Slate', swatch: '#15181c' },
  { id: 'umber', label: 'Umber', swatch: '#1c1714' },
  { id: 'moss', label: 'Moss', swatch: '#171b17' },
  { id: 'wine', label: 'Wine', swatch: '#1c1518' },
  { id: 'ash', label: 'Ash', swatch: '#1b1b1b' },
] as const
export type ColorScheme = typeof COLOR_SCHEMES[number]['id'] | 'custom'
// The app's error color, and a darker one for light backgrounds where the usual pink would not read.
const DANGER = '#e9b8aa', DANGER_ON_LIGHT = '#a3321f'
export const PALETTE_KEYS = ['accent', 'background', 'surface', 'text'] as const
export const defaultPalette: Palette = { accent: '#c5a46d', background: '#191816', surface: '#201f1c', text: '#ede5d6' }
export const validHex = (value: unknown): value is string => typeof value === 'string' && /^#[\da-f]{6}$/i.test(value)
export function validPalette(value: unknown): value is Palette {
  if (!value || typeof value !== 'object') return false
  return PALETTE_KEYS.every(key => validHex((value as Palette)[key]))
}
const channels = (hex: string) => [1, 3, 5].map(offset => parseInt(hex.slice(offset, offset + 2), 16))

function luminance(hex: string) {
  const rgb = channels(hex).map(value => { const s = value / 255; return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4 })
  return rgb[0] * .2126 + rgb[1] * .7152 + rgb[2] * .0722
}
export function contrast(left: string, right: string) {
  const a = luminance(left), b = luminance(right)
  return (Math.max(a, b) + .05) / (Math.min(a, b) + .05)
}
function mix(left: string, right: string, weight: number) {
  const second = channels(right)
  return '#' + channels(left).map((value, index) => Math.round(value * (1 - weight) + second[index] * weight).toString(16).padStart(2, '0')).join('')
}
const inkOn = (color: string) => contrast(color, '#ffffff') > contrast(color, '#000000') ? '#ffffff' : '#000000'
function readableMix(background: string, text: string, minimum: number) {
  for (const weight of [.6, .75, .9, 1]) {
    const mixed = mix(background, text, weight)
    if (contrast(background, mixed) >= minimum) return mixed
  }
  return text
}
/** Text needs 4.5:1 and the accent 3:1 against both the background and the surface. */
export function paletteReadability(value: Palette) {
  if (!validPalette(value)) return { valid: false, text: 0, accent: 0 }
  const text = Math.min(contrast(value.text, value.background), contrast(value.text, value.surface))
  const accent = Math.min(contrast(value.accent, value.background), contrast(value.accent, value.surface))
  return { valid: text >= 4.5 && accent >= 3, text, accent }
}
/** The CSS variables a custom palette sets; the rest are worked out from the four colors so they stay readable. */
export function paletteStyles(palette?: Palette | null): Record<string, string> {
  const p = palette && validPalette(palette) ? palette : defaultPalette
  return {
    '--canvas': p.background, '--surface': p.surface, '--text': p.text, '--accent': p.accent,
    '--raised': mix(p.surface, p.text, .06), '--border': readableMix(p.surface, p.text, 3),
    '--muted': readableMix(p.surface, p.text, 4.5), '--faint': readableMix(p.surface, p.text, 4.5),
    '--accent-hover': mix(p.accent, inkOn(p.accent), .1), '--accent-tint': mix(p.surface, p.accent, .15),
    '--on-accent': inkOn(p.accent), '--label': mix(p.text, p.surface, .1), '--user-text': mix(p.text, p.surface, .15),
    '--danger': contrast(DANGER, p.surface) >= 4.5 ? DANGER : DANGER_ON_LIGHT, 'color-scheme': luminance(p.background) > .45 ? 'light' : 'dark',
  }
}

