import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { SETTINGS_KEY, useWorkspaceSettings } from '../../companion'
import type { WorkspaceSettings } from '../../types'
import { Toggle } from '../../components/Fields'
import { Notice } from '../../components/Feedback'

/** The note under a group message when someone lets a secret slip (companion/secrets.py). On by default. */
export function SecretSlipSetting() {
  const client = useQueryClient()
  const settings = useWorkspaceSettings()
  const [error, setError] = useState('')
  const save = async (show_secret_slips: boolean) => {
    setError('')
    try { client.setQueryData(SETTINGS_KEY, await api<WorkspaceSettings>('/settings', { show_secret_slips }, 'PUT')) }
    catch (failure) { setError(failure instanceof Error ? failure.message : 'That setting was not saved.') }
  }
  return (
    <section className="settings-section form-stack" aria-labelledby="secret-slip-heading">
      <h2 id="secret-slip-heading">Group chats</h2>
      <Toggle label="Say when a secret slips out" checked={settings.data?.show_secret_slips !== false} onChange={(checked) => void save(checked)}
        hint="A note under the message when someone lets a secret slip. Turned off, you only find out from what they say; everyone there still knows it, and Secrets on the Groups page still shows who knows." />
      {error && <Notice tone="error">{error}</Notice>}
    </section>
  )
}
