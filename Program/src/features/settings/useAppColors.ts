import { useEffect } from 'react'
import { useWorkspaceSettings } from '../../companion'
import { paletteStyles } from './palette'

/** Puts the saved color scheme on the page root, so dialogs and menus outside the app shell follow it too. */
export function useAppColors() {
  const settings = useWorkspaceSettings().data
  const scheme = settings?.color_scheme ?? 'ink'
  const palette = settings?.custom_palette
  useEffect(() => {
    const root = document.documentElement
    root.dataset.theme = scheme
    const styles = scheme === 'custom' ? paletteStyles(palette) : {}
    for (const [name, value] of Object.entries(styles)) root.style.setProperty(name, value)
    return () => { for (const name of Object.keys(styles)) root.style.removeProperty(name) }
  }, [scheme, palette])
}
