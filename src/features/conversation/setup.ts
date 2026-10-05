import type { Companion, Connection } from '../../types'
import type { View } from '../../companion'

export interface SetupStep { id: string; label: string; detail: string; done: boolean; optional: boolean; view: View }

/** The first-conversation checklist (PRD "First conversation"): only the model connection is needed to talk. */
export function setupSteps(companion: Companion, connection: Connection | null): SetupStep[] {
  const name = companion.version.name
  const { home_city: city, schedule } = companion.version.definition
  return [
    { id: 'character', label: `Create ${name}`, detail: 'Personality, voice and relationship framing. You can revise them any time.', done: true, optional: false, view: 'character' },
    { id: 'connection', label: 'Connect a text model', detail: connection ? `Using ${connection.model} at ${connection.base_url}.` : `Any OpenAI-compatible service, local or hosted. Until then your messages are saved and ${name} replies once it is connected.`, done: !!connection, optional: false, view: 'settings' },
    { id: 'life', label: `Give ${name} a home and a routine`, detail: 'A city and a weekly routine make their days, posts and replies fit together. Without them they still talk normally.', done: !!city && schedule.length > 0, optional: true, view: 'character' },
  ]
}
