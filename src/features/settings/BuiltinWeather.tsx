import { useState } from 'react'
import type { ContextOverview, ContextServiceInfo } from '../../types'
import { Toggle } from '../../components/Fields'
import { saveBuiltin } from './builtinSave'
import { weatherRunIn, weatherSwitches } from './contextTools'

const DESTINATION = 'the built-in weather program on this computer, which asks Open-Meteo (and the National Weather Service for US places)'

interface Props {
  service: ContextServiceInfo
  data: ContextOverview
  name: string
  refresh: () => Promise<unknown>
  onError: (text: string) => void
}

/**
 * The built-in weather server as two plain switches. One server covers both places; turning a switch on saves the
 * lookup and confirms the disclosure written above the switches.
 */
export function BuiltinWeather({ service, data, name, refresh, onError }: Props) {
  const [busy, setBusy] = useState(false)
  const saved = service.mappings.find((mapping) => mapping.category === 'weather')
  const suggestion = service.suggestions.weather
  const { mine, theirs } = weatherSwitches(saved)
  const change = async (next: { mine: boolean; theirs: boolean }) => {
    if (busy || (!saved && !suggestion)) return
    setBusy(true)
    try {
      await saveBuiltin(service.id, 'weather', weatherRunIn(next.mine, next.theirs), saved, suggestion)
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
