import { useSyncExternalStore } from 'react'

/** Text size, reading font and motion belong to this device, not the workspace: a phone and a 27" monitor want different
 * sizes (Iris, v09-appearance-first-launch.md). Kept in this browser; nothing breaks when storage is unavailable. */
export type ReadingFont = 'default' | 'atkinson' | 'opendyslexic'
export type Motion = 'system' | 'reduce' | 'full'
export interface DeviceLook { textScale: number; font: ReadingFont; fontEverywhere: boolean; motion: Motion }

export const TEXT_SCALE = { min: 85, max: 200, step: 5 } as const
export const DEFAULT_LOOK: DeviceLook = { textScale: 100, font: 'default', fontEverywhere: false, motion: 'system' }
const KEY = 'companion-device-look'
const FONTS: ReadingFont[] = ['default', 'atkinson', 'opendyslexic']
const MOTIONS: Motion[] = ['system', 'reduce', 'full']
const listeners = new Set<() => void>()

export function clampScale(value: number): number {
  if (!Number.isFinite(value)) return DEFAULT_LOOK.textScale
  return Math.min(TEXT_SCALE.max, Math.max(TEXT_SCALE.min, Math.round(value / TEXT_SCALE.step) * TEXT_SCALE.step))
}

/** A saved look with anything unknown or out of range put back to its default. */
export function cleanLook(value: unknown): DeviceLook {
  const saved = (value && typeof value === 'object' ? value : {}) as Partial<DeviceLook>
  return {
    textScale: clampScale(Number(saved.textScale ?? DEFAULT_LOOK.textScale)),
    font: FONTS.includes(saved.font as ReadingFont) ? saved.font as ReadingFont : DEFAULT_LOOK.font,
    fontEverywhere: saved.fontEverywhere === true,
    motion: MOTIONS.includes(saved.motion as Motion) ? saved.motion as Motion : DEFAULT_LOOK.motion,
  }
}

let current: DeviceLook | null = null

export function readLook(): DeviceLook {
  if (current) return current
  try {
    current = cleanLook(JSON.parse(localStorage.getItem(KEY) ?? 'null'))
  } catch {
    current = DEFAULT_LOOK
  }
  return current
}

export function saveLook(change: Partial<DeviceLook>) {
  current = cleanLook({ ...readLook(), ...change })
  try { localStorage.setItem(KEY, JSON.stringify(current)) } catch { /* kept for this visit only */ }
  applyLook(current)
  listeners.forEach((listener) => listener())
}

/** The page root carries the look, so every screen and dialog follows it (styles.css: data-font, data-motion). */
export function applyLook(look: DeviceLook) {
  const root = document.documentElement
  root.style.fontSize = look.textScale === 100 ? '' : `${look.textScale}%`
  root.dataset.font = look.font
  root.dataset.fontEverywhere = String(look.fontEverywhere && look.font !== 'default')
  root.dataset.motion = look.motion
  // From 150% the desktop nav rail shows icons only (their names stay for screen readers).
  root.dataset.textLarge = String(look.textScale >= 150)
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}

export function useDeviceLook(): DeviceLook {
  return useSyncExternalStore(subscribe, readLook, () => DEFAULT_LOOK)
}
