import { appDate } from '../../appTime.ts'
import type { CareerSummary } from '../../types'

/** The careers of their era; adult work only while the adult side of life is on. Their current one always stays. */
export function careersFor(careers: CareerSummary[], era: string | undefined, current: string, adult = false): CareerSummary[] {
  const fitting = careers.filter((career) => career.id === current || ((!era || career.eras.includes(era)) && (adult || !career.adult)))
  return [...fitting].sort((a, b) => a.name.localeCompare(b.name))
}

export function todayIso(now = appDate()): string {
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}
