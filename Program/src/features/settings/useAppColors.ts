import { useEffect, useSyncExternalStore } from 'react'
import { useWorkspaceSettings } from '../../companion'
import type { WorkspaceSettings } from '../../types'
import { paletteStyles } from './palette'

const LIGHT_QUERY = '(prefers-color-scheme: light)'

function subscribe(change: () => void) {
  const query = window.matchMedia(LIGHT_QUERY)
  query.addEventListener('change', change)
  return () => query.removeEventListener('change', change)
}

/** Whether the computer is set to light, kept up to date when it changes (an evening switch to dark, say). */
function useComputerLight() {
  return useSyncExternalStore(subscribe, () => window.matchMedia(LIGHT_QUERY).matches, () => false)
}

/** Puts the saved look on the page root, so dialogs and menus outside the app shell follow it too: the color profile
 * (Light, or the dark profile, following the computer unless the user picked one), the text size, the reading font
 * and how much things move. */
export function useAppColors() {
  const settings = useWorkspaceSettings().data
  const light = useComputerLight()
  const { scheme, palette, scale, font, motion } = look(settings, light)
  useEffect(() => {
    const root = document.documentElement
    root.dataset.theme = scheme
    const styles = scheme === 'custom' ? paletteStyles(palette) : {}
    for (const [name, value] of Object.entries(styles)) root.style.setProperty(name, value)
    return () => { for (const name of Object.keys(styles)) root.style.removeProperty(name) }
  }, [scheme, palette])
  useEffect(() => {
    const root = document.documentElement
    root.style.fontSize = scale === 100 ? '' : `${scale}%`
    root.dataset.font = font
    root.dataset.motion = motion
  }, [scale, font, motion])
}

const DEFAULTS = { theme: 'system', color_scheme: 'ink', text_scale: 100, reading_font: 'default', motion: 'system' } as const

/** The saved look with its defaults, and the profile showing now. */
function look(settings: WorkspaceSettings | undefined, light: boolean) {
  const saved = { ...DEFAULTS, ...settings }
  const scheme = saved.theme === 'light' || (saved.theme === 'system' && light) ? 'light' : saved.color_scheme
  return { scheme, palette: saved.custom_palette, scale: saved.text_scale, font: saved.reading_font, motion: saved.motion }
}
