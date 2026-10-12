import type { View } from '../../companion'
import type { Connection } from '../../types'

export interface WelcomeStep { id: string; label: string; detail: string; done: boolean; action: string; primary: boolean; view: View }
/** Where "Set it up for me" stands on this computer: offered, under way, just cancelled (Undo still showing), or not
 * part of the welcome. */
export type SetUp = 'offer' | 'active' | 'cancelled' | null

const SERVICE_DETAIL = 'A hosted service such as OpenAI, Anthropic or OpenRouter, your Codex login, or a model on this computer. It writes their replies and helps you create them.'
const LOCAL_DETAIL = 'A free model that runs on your graphics card, so your chats stay on this computer. Or use a service such as OpenRouter or your Codex login.'

/** Connecting a model comes first: the quick start, the paste box, the sidecar and every reply need one.
 * `connection` is undefined while it is still loading. While the model downloads, creating them is the next step. */
export function welcomeSteps(connection: Connection | null | undefined, setUp: SetUp = null, builtin = '', getWording = false): WelcomeStep[] {
  return [modelStep(connection, !connection && setUp !== null, builtin, getWording), characterStep(connection, !connection && setUp === 'active')]
}

/** `builtin` names the model "Set it up for me" made the chat model, said the way the user knows it. */
function modelStep(connection: Connection | null | undefined, local: boolean, builtin: string, getWording: boolean): WelcomeStep {
  const step = { id: 'model', done: !!connection, view: 'settings/models' as View }
  if (connection && builtin) return { ...step, label: '1. Get a text model', primary: false, detail: `Using ${builtin} on this computer.`, action: 'Change' }
  if (connection) return { ...step, label: getWording ? '1. Get a text model' : '1. Connect a text model', primary: false, detail: `Using ${connection.model} through ${connection.provider_name}.`, action: 'Change' }
  if (local) return { ...step, label: '1. Get a text model', primary: false, detail: LOCAL_DETAIL, action: '' }
  return { ...step, label: '1. Connect a text model', primary: connection === null, detail: SERVICE_DETAIL, action: connection === null ? 'Set up a model' : '' }
}

function characterStep(connection: Connection | null | undefined, downloading: boolean): WelcomeStep {
  const ready = !!connection || downloading
  return {
    id: 'character', label: '2. Create your companion', done: false, view: 'character', primary: ready,
    detail: downloading ? "Your model isn't ready yet. Fill in what you like; whatever's left gets written when it's ready."
      : 'Pick a name, an age and where and when they live, and your text model writes the rest. Or import a character you already have.',
    action: ready ? 'Create your companion' : connection === null ? 'Create without a model for now' : '',
  }
}

export const welcomeLede = (setUp: SetUp) => setUp
  ? 'Two steps: get the model your companion thinks with, then create them. You can change everything later.'
  : 'Two steps: connect the text model your companion thinks with, then create them. You can change everything later.'
