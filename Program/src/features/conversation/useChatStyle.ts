import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { SETTINGS_KEY, useWorkspaceSettings } from '../../companion'
import type { WorkspaceSettings } from '../../types'
import { chatStyleOf, retroDarkOn, soundsOn } from './chatStyles'

/** The saved style, and a save that shows the change at once and puts the saved state back if it is refused. */
export function useChatStyle() {
  const client = useQueryClient()
  const settings = useWorkspaceSettings()
  const save = async (change: Partial<Pick<WorkspaceSettings, 'chat_style' | 'chat_sounds' | 'chat_retro_dark' | 'color_scheme' | 'custom_palette'>>) => {
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
  return { style: chatStyleOf(settings.data), scheme: settings.data?.color_scheme ?? 'ink', palette: settings.data?.custom_palette ?? null, sounds: soundsOn(settings.data), soundsSetting: !!settings.data?.chat_sounds,
    retroDark: retroDarkOn(settings.data), retroDarkSetting: !!settings.data?.chat_retro_dark, save }
}
