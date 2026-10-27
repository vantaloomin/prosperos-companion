import { api } from '../../../api'
import { Toggle } from '../../../components/Fields'
import { isRecall, type ModelsOverview, type ModelMix as Mix } from './types'

const OFF: Mix = { enabled: false, mode: 'random', profile_ids: [] }

/** The Conversation profile and one other: a mix that works the moment it is turned on. */
function starter(chat: string | undefined, ids: string[]) {
  return [...(chat && ids.includes(chat) ? [chat] : []), ...ids.filter(id => id !== chat)].slice(0, 2)
}

/** Mix models in chat (like a rotation): each reply comes from one of the chosen profiles, at random or in turn, with
 * that profile's own model and settings. Off by default; with fewer than two finished profiles the Conversation
 * profile answers. */
export function ModelMix({ overview, onChanged, onError }: { overview: ModelsOverview; onChanged: (data?: ModelsOverview) => void; onError: (text: string) => void }) {
  const mix = overview.mix?.chat ?? OFF
  const ready = overview.profiles.filter(profile => profile.ready && !isRecall(profile.config))
  if (ready.length < 2) return null
  const save = async (change: Partial<Mix>) => {
    const next = { ...mix, ...change }
    // Turning it on with nothing picked starts from the Conversation profile and the newest other one.
    if (next.enabled && !next.profile_ids.length) next.profile_ids = starter(overview.routes.chat, ready.map(profile => profile.id))
    try { onChanged(await api<ModelsOverview>('/models/mix', { job: 'chat', ...next }, 'PUT')) } catch (error) { onError(error instanceof Error ? error.message : 'Not changed.') }
  }
  const toggle = (id: string, on: boolean) => void save({ profile_ids: on ? [...mix.profile_ids, id] : mix.profile_ids.filter(item => item !== id) })
  const safeOnly = ready.filter(profile => mix.profile_ids.includes(profile.id) && profile.config.provider === 'claude_code')
  // The picks and order sit inside the toggle, lined up with its hint (Iris).
  return <div className="model-mix">
    <Toggle label="Mix models in chat" checked={mix.enabled} onChange={value => void save({ enabled: value })} hint="Each reply comes from one of the profiles you pick, with that profile's own model and settings, for more variety. Other jobs keep their own profile.">
      {mix.enabled && <div className="model-mix-options form-stack">
        <fieldset className="plain-fieldset"><legend className="field-label">Profiles in the mix</legend>
          {ready.map(profile => <label key={profile.id} className="checkbox-row"><input type="checkbox" checked={mix.profile_ids.includes(profile.id)} onChange={event => toggle(profile.id, event.target.checked)} />{profile.name}</label>)}
          {mix.profile_ids.length < 2 && <small>Pick at least two. Until then the Conversation profile answers.</small>}
          {safeOnly.length > 0 && <small>{safeOnly.map(profile => profile.name).join(', ')} won’t write the adult side of life, so those replies stay non-explicit.</small>}
        </fieldset>
        <fieldset className="plain-fieldset"><legend className="field-label">Order</legend>
          <div className="segmented">
            {([['random', 'At random'], ['in_turn', 'In turn']] as const).map(([value, label]) => <label key={value}>
              <input type="radio" className="visually-hidden" name="model-mix-mode" value={value} checked={mix.mode === value} onChange={() => void save({ mode: value })} /><span>{label}</span>
            </label>)}
          </div>
          <small>At random can repeat a model. In turn goes through them one after another.</small>
        </fieldset>
      </div>}
    </Toggle>
  </div>
}
