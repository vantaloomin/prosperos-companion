import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { View } from '../../companion'
import { useWorkspaceSettings } from '../../companion'
import type { LifeSettings, World } from '../../types'
import { matchPreset } from '../settings/presetChoices'
import { LIFE_KEY } from '../settings/useLifeSettings'
import { enter } from '../worlds/useWorlds'

/** The realism preset is the user's, not the world's: said once, not asked again. */
export function FeelsLike({ go }: { go: (view: View) => void }) {
  const workspace = useWorkspaceSettings()
  const life = useQuery({ queryKey: LIFE_KEY, queryFn: () => api<LifeSettings>('/life/settings') })
  if (!life.data || !workspace.data) return null
  const label = matchPreset(life.data, workspace.data)?.label ?? 'Your own mix'
  return (
    <p className="welcome-feels subtle">Feels like: {label} · <button type="button" className="text-button" onClick={() => go('settings/realism')}>Change in Settings &gt; Realism</button></p>
  )
}

/** A way out for someone who opened a new world by accident. */
export function BackTo({ world }: { world: World }) {
  const back = async () => { await api(`/worlds/${world.id}/switch`, {}); enter() }
  return <p className="welcome-back"><button type="button" className="text-button" onClick={() => void back()}>Back to {world.name}</button></p>
}
