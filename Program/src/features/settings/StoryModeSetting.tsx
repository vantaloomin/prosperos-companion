import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { SETTINGS_KEY, useWorkspaceSettings } from '../../companion'
import type { WorkspaceSettings } from '../../types'
import { Toggle } from '../../components/Fields'
import { Notice } from '../../components/Feedback'

/** Story mode is opt-in: an extra beside the companion, so it stays out of sight until turned on. */
export function StoryModeSetting() {
  const client = useQueryClient()
  const settings = useWorkspaceSettings()
  const [error, setError] = useState('')
  const save = async (story_mode: boolean) => {
    setError('')
    try { client.setQueryData(SETTINGS_KEY, await api<WorkspaceSettings>('/settings', { story_mode }, 'PUT')) }
    catch (failure) { setError(failure instanceof Error ? failure.message : 'That setting was not saved.') }
  }
  return (
    <section className="settings-section form-stack" aria-labelledby="story-mode-heading">
      <h2 id="story-mode-heading">Story mode</h2>
      <Toggle label="Show the Story tab" checked={!!settings.data?.story_mode} onChange={(checked) => void save(checked)}
        hint="An experimental extra: your own story around the cities, told by a narrator, where you meet the townsfolk yourself. Your companion never sees it." />
      {error && <Notice tone="error">{error}</Notice>}
    </section>
  )
}
