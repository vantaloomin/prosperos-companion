import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import type { LifeSettings } from '../../types'
import { DRAMA_LEVELS } from '../today/storyText'
import { useWorlds } from '../worlds/useWorlds'
import { Field } from '../../components/Fields'
import { ErrorNotice } from '../../components/ErrorNotice'
import { SectionPending } from '../../components/SectionPending'
import { LIFE_KEY, useLifeSettings } from './useLifeSettings'

const SAME = 'realism'

/** How much happens in this world (companion/life/world_drama.py): its own drama level, or the one in Realism.
 * Life settings follow the user into every world; this one stays in the world it was set in. */
export function WorldDrama({ name }: { name: string }) {
  const client = useQueryClient()
  const { settings, data } = useLifeSettings()
  const world = useWorlds().data?.world.name
  const [error, setError] = useState<Error | null>(null)
  if (!data) return <SectionPending queries={[settings]} heading="world-life-heading" title="This world" />
  const realism = DRAMA_LEVELS[data.drama] ?? DRAMA_LEVELS[1]
  const own = data.world_drama === null ? null : DRAMA_LEVELS[data.world_drama]
  const save = async (value: string) => {
    try {
      const saved = await api<LifeSettings>('/life/world', { drama: value === SAME ? null : Number(value) }, 'PUT')
      client.setQueryData(LIFE_KEY, saved)
      void client.invalidateQueries({ queryKey: ['today'] })
      setError(null)
    } catch (caught) { setError(caught instanceof Error ? caught : new Error('Not saved.')) }
  }
  const alone = data.alone && name
    ? ` ${name} is the only companion here, so a little more happens to them than to someone with others around.` : ''
  return (
    <section className="settings-section form-stack" aria-labelledby="world-life-heading">
      <h2 id="world-life-heading">This world</h2>
      <Field label={`How much happens${world ? ` in ${world}` : ''}`}
        hint={`${(own ?? realism).hint} Only for this world. Your other worlds stay as they are.${alone}`}>
        {(id, describedBy) => (
          <select id={id} aria-describedby={describedBy} value={data.world_drama ?? SAME} onChange={(event) => void save(event.target.value)}>
            <option value={SAME}>Same as in Realism ({realism.label})</option>
            {DRAMA_LEVELS.map((level) => <option key={level.value} value={level.value}>{level.label}</option>)}
          </select>
        )}
      </Field>
      {error && <ErrorNotice error={error} />}
    </section>
  )
}
