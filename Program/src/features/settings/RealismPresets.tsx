import { useId, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { SETTINGS_KEY, useWorkspaceSettings } from '../../companion'
import type { LifeSettings, WorkspaceSettings } from '../../types'
import { Notice } from '../../components/Feedback'
import { SectionPending } from '../../components/SectionPending'
import { GROUPS_KEY } from '../groups/groupState'
import { REALISM_PRESETS, matchPreset, type RealismPreset } from './presetChoices'
import { LIFE_KEY, type SaveResult } from './useLifeSettings'

/** Wolfenstein-style starting points (src/features/settings/presetChoices.ts); a tap applies one, and any change after is your own mix. */
export function RealismPresets({ heading, title, intro }: { heading: string; title: string; intro?: string }) {
  const client = useQueryClient()
  const workspace = useWorkspaceSettings()
  const life = useQuery({ queryKey: LIFE_KEY, queryFn: () => api<LifeSettings>('/life/settings') })
  const [result, setResult] = useState<SaveResult>(null)
  const [applying, setApplying] = useState<string | null>(null)
  const name = useId()
  if (!life.data || !workspace.data) return <SectionPending queries={[life, workspace]} heading={heading} title={title} />
  const current = matchPreset(life.data, workspace.data)
  const apply = async (preset: RealismPreset) => {
    setApplying(preset.id)
    try {
      client.setQueryData(LIFE_KEY, await api<LifeSettings>('/life/settings', preset.life, 'PUT'))
      client.setQueryData(SETTINGS_KEY, await api<WorkspaceSettings>('/settings', preset.shown, 'PUT'))
      for (const queryKey of [['today'], ['news'], ['reactions'], GROUPS_KEY, ['group']]) void client.invalidateQueries({ queryKey })
      setResult({ tone: 'info', text: `${preset.label}: saved. Fine-tune it any time in Settings > Realism.` })
    } catch (error) {
      setResult({ tone: 'error', text: error instanceof Error ? error.message : 'Not saved.' })
    }
    setApplying(null)
  }
  const picked = applying ?? current?.id
  return (
    <section className="settings-section form-stack" aria-labelledby={heading}>
      <div>
        <h2 id={heading}>{title}</h2>
        <p className="subtle">{intro ?? (current ? 'Pick how you want it to feel. Closeness stays as you set it for each companion.' : 'Your own mix right now. Pick one to start over from it. Closeness stays as you set it for each companion.')}</p>
      </div>
      <fieldset className="chat-style-options realism-presets">
        <legend className="visually-hidden">Realism preset</legend>
        {REALISM_PRESETS.map((preset) => (
          <label key={preset.id} className="chat-style-option">
            <input type="radio" name={name} value={preset.id} checked={picked === preset.id} onChange={() => void apply(preset)} />
            <span className="chat-style-text"><span>{preset.label}</span><small>{preset.description}</small></span>
          </label>
        ))}
      </fieldset>
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
    </section>
  )
}
