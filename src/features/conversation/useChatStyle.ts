import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { SETTINGS_KEY, useWorkspaceSettings } from '../../companion'
import type { WorkspaceSettings } from '../../types'
import { chatStyleOf, soundsOn } from './chatStyles'

/** The saved style, and a save that shows the change at once and puts the saved state back if it is refused. */
export function useChatStyle() {
  const client = useQueryClient()
  const settings = useWorkspaceSettings()
  const save = async (change: Pick<WorkspaceSettings, 'chat_style' | 'chat_sounds'>) => {
    const before = client.getQueryData<WorkspaceSettings>(SETTINGS_KEY)
    if (before) client.setQueryData(SETTINGS_KEY, { ...before, ...change })
    try {
      client.setQueryData(SETTINGS_KEY, await api<WorkspaceSettings>('/settings', change, 'PUT'))
      return null
    } catch (error) {
      if (before) client.setQueryData(SETTINGS_KEY, before)
      return error instanceof Error ? error.message : 'That setting was not saved.'
    }
  }
  return { style: chatStyleOf(settings.data), sounds: soundsOn(settings.data), soundsSetting: !!settings.data?.chat_sounds, save }
}
