import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { SETTINGS_KEY, useWorkspaceSettings } from '../../companion'
import type { LifeSettings, WorkspaceSettings } from '../../types'
import { Toggle } from '../../components/Fields'
import { Notice } from '../../components/Feedback'
import { GROUPS_KEY } from '../groups/groupState'

type Flag = 'show_moods' | 'show_news' | 'show_odds' | 'show_secret_slips'
const LIFE_KEY = ['life-settings']

/** Hidden values: what companions feel, who has heard their news and the odds behind how things went shape every
 * reply, but stay unseen unless the user turns them on, so by default you find out the way you would in life. */
export function HiddenValues({ name }: { name: string }) {
  const client = useQueryClient()
  const settings = useWorkspaceSettings()
  const life = useQuery({ queryKey: LIFE_KEY, queryFn: () => api<LifeSettings>('/life/settings') })
  const [error, setError] = useState('')
  const flag = (key: Flag, shown = false) => settings.data?.[key] ?? shown
  const refresh = () => {
    for (const queryKey of [['today'], ['news'], ['reactions'], GROUPS_KEY, ['group']]) void client.invalidateQueries({ queryKey })
  }
  const save = async (change: Partial<Record<Flag, boolean>>) => {
    setError('')
    try { client.setQueryData(SETTINGS_KEY, await api<WorkspaceSettings>('/settings', change, 'PUT')); refresh() }
    catch (failure) { setError(failure instanceof Error ? failure.message : 'That setting was not saved.') }
  }
  const saveMind = async (on_her_mind: boolean) => {
    setError('')
    try { client.setQueryData(LIFE_KEY, await api<LifeSettings>('/life/settings', { on_her_mind }, 'PUT')); refresh() }
    catch (failure) { setError(failure instanceof Error ? failure.message : 'That setting was not saved.') }
  }
  const { who, whose, keeps } = phrases(name)
  return (
    <section className="settings-section form-stack" aria-labelledby="hidden-values-heading">
      <div>
        <h2 id="hidden-values-heading">Hidden values</h2>
        <p className="subtle">Some things stay behind the curtain so it feels like real life: you notice them from how people talk, not from a label. They still shape every reply when hidden.</p>
      </div>
      <Toggle label="Show how they're feeling" checked={flag('show_moods')} onChange={(checked) => void save({ show_moods: checked })}
        hint={`On Today: how ${who} feels and why, how they're doing physically, and how they took what you did lately. In group chats: how each person seems. Off: you only find out from how they talk to you.`} />
      <Toggle label="Show who has heard their news" checked={flag('show_news')} onChange={(checked) => void save({ show_news: checked })}
        hint={`"Word getting around" on Today: who has heard ${whose} news so far, and from whom. Off: word still travels, you just aren't told.`} />
      <Toggle label="Show the odds behind what happens" checked={flag('show_odds')} onChange={(checked) => void save({ show_odds: checked })}
        hint={'"Why it went this way" under storylines, chapters and reactions on Today: the odds for each way it could have gone, and a way to make it go another way.'} />
      <Toggle label={`Show what's on ${whose} mind`} checked={life.data?.on_her_mind !== false} disabled={!life.data} onChange={(checked) => void saveMind(checked)}
        hint={`Each evening Today gets one private thought, worked out from what happened in ${whose} day. Folded until you open it, never part of the chat, and never anything ${keeps} secret.`} />
      <Toggle label="Say when a secret slips out" checked={flag('show_secret_slips', true)} onChange={(checked) => void save({ show_secret_slips: checked })}
        hint="A note under a group message when someone lets a secret slip. Off: you only find out from what they say; everyone there still knows it, and Secrets on the Groups page still shows who knows." />
      {error && <Notice tone="error">{error}</Notice>}
    </section>
  )
}

/** "Mira", "Mira's", "Mira keeps"; with no companion yet, "your companions", "their", "they keep". */
function phrases(name: string) {
  return name ? { who: name, whose: `${name}'s`, keeps: `${name} keeps` } : { who: 'your companions', whose: 'their', keeps: 'they keep' }
}
