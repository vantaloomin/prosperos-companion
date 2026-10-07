import type { View } from '../../companion'
import type { Connection } from '../../types'

export interface WelcomeStep { id: string; label: string; detail: string; done: boolean; action: string; primary: boolean; view: View }

/** Connecting a model comes first: the quick start, the paste box, the sidecar and every reply need one.
 * `connection` is undefined while it is still loading. */
export function welcomeSteps(connection: Connection | null | undefined): WelcomeStep[] {
  const connected = !!connection
  return [
    {
      id: 'model', label: '1. Connect a text model', done: connected, view: 'settings/models', primary: connection === null,
      detail: connection ? `Using ${connection.model} through ${connection.provider_name}.` : 'A hosted service such as OpenAI, Anthropic or OpenRouter, your Codex login, or a model on this computer. It writes their replies and helps you create them.',
      action: connection ? 'Change' : connection === null ? 'Set up a model' : '',
    },
    {
      id: 'character', label: '2. Create your companion', done: false, view: 'character', primary: connected,
      detail: 'Pick a name, an age and where and when they live, and your text model writes the rest. Or import a character you already have.',
      action: connected ? 'Create your companion' : connection === null ? 'Create without a model for now' : '',
    },
  ]
}
