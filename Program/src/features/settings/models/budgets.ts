import type { ProfileConfig } from './types'

// Bounded choices for a profile's budgets (Iris, #535): context size and time limit as presets, the longest reply
// as a slider. A saved or reported value that is not a preset is kept as one more choice, so nothing changes by itself.

const CONTEXTS = [4096, 8192, 16384, 32768, 65536, 131072, 200000, 1000000]
const TIMES = [60, 120, 180, 300, 600]

/** 16000 and 16384 are both "16K"; 1,000,000 is "1M". */
export function shortTokens(tokens: number): string {
  if (tokens >= 1_000_000) return `${+(tokens / 1_000_000).toFixed(1)}M`
  return `${Math.round(tokens / 1000)}K`
}

type Choice = { value: number; label: string }

function withExtras(presets: Choice[], extras: Choice[]): Choice[] {
  const all = [...presets]
  for (const extra of extras) if (!all.some(choice => choice.value === extra.value)) all.push(extra)
  return all.sort((a, b) => a.value - b.value)
}

export function contextChoices(saved: number, reported?: number | null): Choice[] {
  const extras: Choice[] = [{ value: saved, label: `${saved.toLocaleString()} tokens` }]
  if (reported) extras.push({ value: reported, label: `${reported.toLocaleString()} tokens (reported)` })
  return withExtras(CONTEXTS.map(value => ({ value, label: shortTokens(value) })), extras)
}

const minutes = (seconds: number) => seconds % 60 ? `${seconds} s` : `${seconds / 60} min`

export function timeChoices(saved: number): Choice[] {
  return withExtras(TIMES.map(value => ({ value, label: minutes(value) })), [{ value: saved, label: minutes(saved) }])
}

/** 200 to 8,000 in steps of 100, stretched to hold a saved value outside it. */
export function replyRange(saved: number) {
  return { min: Math.min(200, saved), max: Math.max(8000, saved), step: 100 }
}

/** The fold's summary value: "16K context · 800 reply", and the effort when one is set. */
export function generationSummary(config: ProfileConfig): string {
  const parts = [`${shortTokens(config.context_tokens)} context`, `${config.max_output_tokens.toLocaleString()} reply`]
  if (config.reasoning_effort) parts.push(`${config.reasoning_effort.charAt(0).toUpperCase()}${config.reasoning_effort.slice(1)} effort`)
  return parts.join(' · ')
}
