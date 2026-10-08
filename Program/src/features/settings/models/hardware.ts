import { useQuery } from '@tanstack/react-query'
import { api } from '../../../api'

export interface Gpu { index: number; name: string; memory_gb: number; usable_gb: number; used_gb: number | null; shared: boolean }
export type Area = 'computer' | 'text' | 'images'
export interface HardwareWarning { area: Area; tone: 'warning' | 'tip'; text: string }
export interface HardwareReport {
  computer: { system: string; cores: number; memory_gb: number | null; gpus: Gpu[]; gpu_note: string | null }
  can_run: string[]
  warnings: HardwareWarning[]
}

export const HARDWARE_KEY = ['hardware']
export const gb = (value: number) => value >= 10 ? `${Math.round(value)} GB` : `${value.toFixed(1)} GB`

/** The server scans this computer (companion/hardware.py) and checks the models set up against it. */
export function useHardware() {
  return useQuery({ queryKey: HARDWARE_KEY, queryFn: () => api<HardwareReport>('/hardware') })
}
