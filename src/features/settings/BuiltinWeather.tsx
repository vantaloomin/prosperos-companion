import { useState } from 'react'
import { api } from '../../api'
import type { ContextMapping, ContextOverview, ContextPurpose, ContextServiceInfo, MappingSuggestion } from '../../types'
import { Toggle } from '../../components/Fields'
import { weatherRunIn, weatherSwitches } from './contextTools'

const DESTINATION = 'the built-in weather program on this computer, which asks Open-Meteo (and the National Weather Service for US places)'

interface Props {
  service: ContextServiceInfo
  data: ContextOverview
  name: string
  refresh: () => Promise<unknown>
  onError: (text: string) => void
}

/** Save when the lookup runs and confirm its disclosure, or turn it off when neither place is chosen. */
async function save(path: string, run_in: ContextPurpose[], saved?: ContextMapping, suggestion?: MappingSuggestion) {
  if (run_in.length === 0) return api(`${path}/disable`, {})
  const base = saved ?? suggestion!
  const updated = await api<ContextServiceInfo>(path, { tool: base.tool, arguments: base.arguments, run_in }, 'PUT')
  const mapping = updated.mappings.find((item) => item.category === 'weather')
  if (mapping) await api(`${path}/enable`, { digest: mapping.disclosure.digest })
}

/**
 * The built-in weather server as two plain switches. One server covers both places; turning a switch on saves the
 * lookup and confirms the disclosure written above the switches, so nothing is sent before it is described.
 */
export function BuiltinWeather({ service, data, name, refresh, onError }: Props) {
  const [busy, setBusy] = useState(false)
  const saved = service.mappings.find((mapping) => mapping.category === 'weather')
  const suggestion = service.suggestions.weather
  const { mine, theirs } = weatherSwitches(saved)
  const path = `/context/services/${service.id}/tools/weather`
  const change = async (next: { mine: boolean; theirs: boolean }) => {
    if (busy || (!saved && !suggestion)) return
    setBusy(true)
    try {
      await save(path, weatherRunIn(next.mine, next.theirs), saved, suggestion)
      await refresh()
    } catch (error) { onError(error instanceof Error ? error.message : 'Not saved.') } finally { setBusy(false) }
  }
  const yours = data.location.user_place
  const theirsPlace = data.companion_place
  return (
    <div className="context-mapping form-stack">
      <p className="subtle">
        A switch sends only that place's name to {saved?.disclosure.destination ?? DESTINATION}, when the weather comes up.
        It never sends your conversation, memories or name. When you both live in the same place, one lookup serves both.
      </p>
      <Toggle label={`Your weather (${yours || 'set your city or region above'})`} checked={mine} disabled={busy || (!yours && !mine)}
        hint="When you ask about the weather in chat." onChange={(value) => void change({ mine: value, theirs })} />
      <Toggle label={`${name}'s weather (${theirsPlace ?? 'not a real-world city'})`} checked={theirs} disabled={busy || (!theirsPlace && !theirs)}
        hint={theirsPlace ? `When you ask about the weather where ${name} is, and for ${name}'s day.` : `Only for a companion who lives in a real, modern city.`}
        onChange={(value) => void change({ mine, theirs: value })} />
    </div>
  )
}
