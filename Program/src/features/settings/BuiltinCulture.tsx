import { useState } from 'react'
import { api } from '../../api'
import type { ContextServiceInfo } from '../../types'
import { TextInput, Toggle } from '../../components/Fields'
import { saveBuiltin } from './builtinSave'
import { cultureRunIn, cultureSwitches } from './contextTools'

const DESTINATION = 'the built-in culture pulse program on this computer, which asks Google News, iTunes, Apple Music, TVmaze, Steam, Open Library, Google Trends, Wikipedia and Reddit'

interface Props {
  service: ContextServiceInfo
  name: string
  refresh: () => Promise<unknown>
  onError: (text: string) => void
}

/** Save or remove the optional TMDB key. A new key needs the lookup confirmed again, so the switches that were on are re-confirmed. */
async function saveKey(service: ContextServiceInfo, secret: string, wasOn: { asked: boolean; daily: boolean }) {
  await api(`/context/services/${service.id}`, { name: service.name, transport: 'stdio', command: service.command, secret: secret || undefined, clear_secret: !secret }, 'PUT')
  const saved = service.mappings.find((mapping) => mapping.category === 'culture')
  const runIn = cultureRunIn(wasOn.asked, wasOn.daily)
  if (runIn.length) await saveBuiltin(service.id, 'culture', runIn, saved, service.suggestions.culture)
}

/**
 * The built-in culture pulse server as two switches, plus an optional TMDB key for what's in theaters with ratings:
 * lookups when you ask, and a daily digest that gives the companion a sense of what's out without being asked.
 * Turning a switch on saves the lookup and confirms the disclosure written above it.
 */
export function BuiltinCulture({ service, name, refresh, onError }: Props) {
  const [busy, setBusy] = useState(false)
  const [key, setKey] = useState('')
  const saved = service.mappings.find((mapping) => mapping.category === 'culture')
  const on = cultureSwitches(saved)
  const unusable = !saved && !service.suggestions.culture
  const change = (next: { asked: boolean; daily: boolean }) =>
    void run(() => saveBuiltin(service.id, 'culture', cultureRunIn(next.asked, next.daily), saved, service.suggestions.culture))
  const run = async (work: () => Promise<unknown>) => {
    if (busy) return
    setBusy(true)
    try { await work(); await refresh() } catch (error) { onError(error instanceof Error ? error.message : 'Not saved.') } finally { setBusy(false) }
  }
  return (
    <div className="context-mapping form-stack">
      <p className="subtle">
        Lookups go to {saved?.disclosure.destination ?? DESTINATION}. When you ask, it sends only which of movies, TV, games, music, books or trends you asked about;
        the daily one sends nothing at all. Neither ever sends your conversation, memories, name or location.
      </p>
      <Toggle label={`Movies, shows, games and what's trending`} checked={on.asked} disabled={busy || unusable}
        hint={`When you ask ${name} about movies, TV, games, music, books or what's trending online.`}
        onChange={(value) => change({ ...on, asked: value })} />
      <Toggle label={`A sense of what's going on`} checked={on.daily} disabled={busy || unusable}
        hint={`Once a day, while background activity is on, so ${name} knows what's out and trending and can bring it up first. Only for a companion living in the present day.`}
        onChange={(value) => change({ ...on, daily: value })} />
      <form className="form-stack" onSubmit={(event) => { event.preventDefault(); void run(() => saveKey(service, key.trim(), on).then(() => setKey(''))) }}>
        <TextInput label={service.has_key ? 'TMDB key (saved; enter a new one to replace it)' : 'TMDB key (optional)'} type="password" value={key} maxLength={4000} onChange={setKey}
          hint="A free key from themoviedb.org adds what's in theaters and coming soon, with ratings. It's kept in your system's credential store and sent only to TMDB." />
        <div className="form-actions">
          <button type="submit" className="button" aria-disabled={busy || !key.trim()}>Save key</button>
          {service.has_key && <button type="button" className="text-button" aria-disabled={busy} onClick={() => void run(() => saveKey(service, '', on))}>Remove key</button>}
        </div>
      </form>
    </div>
  )
}
