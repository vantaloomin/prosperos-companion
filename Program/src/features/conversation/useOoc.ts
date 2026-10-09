import { useWorkspaceSettings } from '../../companion'
import { sidecar } from '../sidecar/store'
import { DEFAULT_OOC_MARKERS, splitOoc } from './ooc'

/**
 * Before a message goes to the companion: any out-of-character aside in it goes to the helper instead, and only
 * the rest is sent. Returns what is left for the companion (empty when the whole message was an aside).
 */
export function useOoc() {
  const settings = useWorkspaceSettings().data
  const on = settings?.ooc_to_helper ?? true
  const markers = settings?.ooc_markers?.length ? settings.ooc_markers : DEFAULT_OOC_MARKERS
  return (text: string): string => {
    if (!on) return text
    const { story, aside } = splitOoc(text, markers)
    if (aside) sidecar.handOff(aside)
    return story
  }
}
