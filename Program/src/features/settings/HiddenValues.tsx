import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { SETTINGS_KEY, useWorkspaceSettings } from '../../companion'
import type { WorkspaceSettings } from '../../types'
import { Toggle } from '../../components/Fields'
import { Notice } from '../../components/Feedback'
import { GROUPS_KEY } from '../groups/groupState'

type Flag = 'show_moods' | 'show_news'

/** Hidden values: what companions feel and who has heard their news shape every reply, but stay unseen unless
 * the user turns them on, so by default you find out the way you would in life. Off by default. */
export function HiddenValues({ name }: { name: string }) {
  const client = useQueryClient()
  const settings = useWorkspaceSettings()
  const [error, setError] = useState('')
  const save = async (change: Partial<Record<Flag, boolean>>) => {
    setError('')
    try {
      client.setQueryData(SETTINGS_KEY, await api<WorkspaceSettings>('/settings', change, 'PUT'))
      for (const queryKey of [['today'], ['news'], GROUPS_KEY, ['group']]) void client.invalidateQueries({ queryKey })
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'That setting was not saved.') }
  }
  const who = name || 'your companions'
  return (
    <section className="settings-section form-stack" aria-labelledby="hidden-values-heading">
      <div>
        <h2 id="hidden-values-heading">Hidden values</h2>
        <p className="subtle">Some things stay behind the curtain so it feels like real life: you notice them from how people talk, not from a label. They still shape every reply when hidden.</p>
      </div>
      <Toggle label="Show how they're feeling" checked={settings.data?.show_moods === true} onChange={(checked) => void save({ show_moods: checked })}
        hint={`A line on Today with how ${who} feels and why, and how each person in a group chat seems. Off: you only find out from how they talk to you.`} />
      <Toggle label="Show who has heard their news" checked={settings.data?.show_news === true} onChange={(checked) => void save({ show_news: checked })}
        hint={`"Word getting around" on Today: who has heard ${name ? `${name}'s` : 'their'} news so far, and from whom. Off: word still travels, you just aren't told.`} />
      {error && <Notice tone="error">{error}</Notice>}
    </section>
  )
}
