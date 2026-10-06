import type { CareerSummary } from '../../types'

/** Careers that fit the home city's era (all of them without a city), keeping the current pick listed. */
export function careersFor(careers: CareerSummary[], era: string | undefined, current: string): CareerSummary[] {
  const fitting = careers.filter((career) => !era || career.eras.includes(era) || career.id === current)
  return [...fitting].sort((a, b) => a.name.localeCompare(b.name))
}

export function todayIso(now = new Date()): string {
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}
