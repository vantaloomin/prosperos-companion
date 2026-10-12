import type { MixValues, TownsfolkMix } from '../../types'

/** Shares as the town would have them, in words, for Settings > Debug > Townsfolk mix (companion/world/mix.py). */

export const BOLDER_LABELS: Record<string, string> = { '-2': 'Much tamer', '-1': 'Tamer', '0': 'As built', '1': 'Bolder', '2': 'Much bolder' }
export const DRIVE_LABELS: Record<string, string> = { '-2': 'Much lower', '-1': 'Lower', '0': 'As built', '1': 'Higher', '2': 'Much higher' }
export const LEVEL_NAMES: Record<string, string> = { reserved: 'reserved', conventional: 'conventional', curious: 'curious', adventurous: 'adventurous', wild: 'wild' }
const MOST_QUEER = 0.95

export function pct(value: number): string {
  const rounded = Math.round(value * 10) / 10
  return `${Number.isInteger(rounded) ? rounded : rounded.toFixed(1)}%`
}

/** Women, men and nonbinary people as shares of everyone, as generators.name draws them in a modern world. */
export function genderShares(mix: Pick<MixValues, 'nonbinary' | 'women'>) {
  const rest = 100 - mix.nonbinary
  return { woman: rest * mix.women / 100, man: rest * (100 - mix.women) / 100, nonbinary: mix.nonbinary }
}

/** Slender, in between and heavier as shares of the three together. */
export function buildShares(mix: Pick<MixValues, 'slender' | 'middle' | 'heavier'>) {
  const total = mix.slender + mix.middle + mix.heavier
  if (!total) return { slender: 0, middle: 0, heavier: 0 }
  return { slender: 100 * mix.slender / total, middle: 100 * mix.middle / total, heavier: 100 * mix.heavier / total }
}

/** Each age band's rates under the mix: the sliders scale every band alike (mix.orientation_band). */
export function bandRates(data: Pick<TownsfolkMix, 'bands' | 'defaults'>, mix: Pick<MixValues, 'gay' | 'bisexual'>) {
  return data.bands.map((band) => {
    const gay = Math.min(band.gay * mix.gay / data.defaults.gay, MOST_QUEER)
    const scale = mix.bisexual / data.defaults.bisexual
    const women = Math.min(band.bisexual_women * scale, MOST_QUEER - gay)
    const men = Math.min(band.bisexual_men * scale, MOST_QUEER - gay)
    return { ages: band.ages, gay: 100 * gay, bisexual: 100 * (women + men) / 2 }
  })
}

export function bandLine(rates: { ages: string; value: number }[]): string {
  return rates.map((rate) => `${rate.ages}: ${pct(rate.value)}`).join(', ')
}

export function sharesLine(shares: Record<string, number> | undefined, names: Record<string, string>): string {
  if (!shares) return ''
  return Object.entries(names).map(([key, name]) => `${pct(shares[key] ?? 0)} ${name}`).join(', ')
}

export function sameMix(a: MixValues, b: MixValues): boolean {
  return (Object.keys(b) as (keyof MixValues)[]).every((key) => Number(a[key]) === Number(b[key]))
}
