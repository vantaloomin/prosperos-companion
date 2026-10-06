import { useState } from 'react'
import type { ContextCategory, ContextMapping, ContextOverview, ContextPurpose, ContextServiceInfo } from '../../types'
import { Toggle } from '../../components/Fields'
import { saveBuiltin } from './builtinSave'
import { weatherRunIn, weatherSwitches } from './contextTools'

const DESTINATION = 'the built-in local pulse program on this computer, which asks Google News, Wikipedia, Reddit, ESPN, MLB and Open-Meteo'

interface Props {
  service: ContextServiceInfo
  data: ContextOverview
  name: string
  refresh: () => Promise<unknown>
  onError: (text: string) => void
}

interface Switch { key: string; category: ContextCategory; label: string; hint: string; checked: boolean; place: string | null; runIn: (on: boolean) => ContextPurpose[] }

/** The three switches: headlines for you, and games and air quality for your place and the companion's city. */
function switches(news: ContextMapping | undefined, events: ContextMapping | undefined, yours: string, theirs: string | null, name: string): Switch[] {
  const on = weatherSwitches(events)
  const mine = yours || 'set your city or region above'
  return [
    { key: 'news', category: 'news', label: `Local headlines (${mine})`, checked: Boolean(news?.enabled && news.approved), place: yours || null,
      hint: "When you ask about the news in chat: headlines for your city or the topic you name, what people are reading on Wikipedia, and your city's subreddit.",
      runIn: (value) => value ? ['conversation'] : [] },
    { key: 'mine', category: 'local_events', label: `Games and air quality near you (${mine})`, checked: on.mine, place: yours || null,
      hint: "When you ask what's on nearby: pro games this week, recent scores and today's air quality.", runIn: (value) => weatherRunIn(value, on.theirs) },
    { key: 'theirs', category: 'local_events', label: `Games and air quality in ${name}'s city (${theirs ?? 'not a real-world city'})`, checked: on.theirs, place: theirs,
      hint: theirs ? `When you ask what's on where ${name} is, and for ${name}'s day.` : 'Only for a companion who lives in a real, modern city.',
      runIn: (value) => weatherRunIn(on.mine, value) },
  ]
}

/**
 * The built-in local pulse server as plain switches. Turning a switch on saves the lookup and confirms the
 * disclosure written above the switches.
 */
export function BuiltinPulse({ service, data, name, refresh, onError }: Props) {
  const [busy, setBusy] = useState(false)
  const news = service.mappings.find((mapping) => mapping.category === 'news')
  const events = service.mappings.find((mapping) => mapping.category === 'local_events')
  const change = async (category: ContextCategory, run_in: ContextPurpose[]) => {
    const saved = category === 'news' ? news : events
    if (busy || (!saved && !service.suggestions[category])) return
    setBusy(true)
    try {
      await saveBuiltin(service.id, category, run_in, saved, service.suggestions[category])
      await refresh()
    } catch (error) { onError(error instanceof Error ? error.message : 'Not saved.') } finally { setBusy(false) }
  }
  return (
    <div className="context-mapping form-stack">
      <p className="subtle">
        A switch sends only a place's name, or the topic you ask about, to {(news ?? events)?.disclosure.destination ?? DESTINATION}.
        It never sends your conversation, memories or name. Game listings come from public scoreboards that can change without notice.
      </p>
      {switches(news, events, data.location.user_place, data.companion_place, name).map((item) => (
        <Toggle key={item.key} label={item.label} checked={item.checked} disabled={busy || (!item.place && !item.checked)} hint={item.hint}
          onChange={(value) => void change(item.category, item.runIn(value))} />
      ))}
    </div>
  )
}
