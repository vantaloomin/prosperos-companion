import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../../api'
import { isRecall, type ModelMix, type ModelProfile, type ModelsOverview } from './types.ts'

const KEY = ['models']
/** The choice that turns the conversation's Mix back on (Settings > Models > Mix models in chat). */
export const MIX = 'mix'

/** The Mix can answer once it holds two finished profiles; it does while it is on. */
function mixInfo(mix: ModelMix | undefined, profiles: ModelProfile[]) {
  const usable = (mix?.profile_ids ?? []).filter(id => profiles.some(profile => profile.id === id)).length
  return { canMix: usable > 1, mixing: usable > 1 && !!mix?.enabled, mixCount: usable }
}

/** The text profiles that can answer in chat and the one that does, so chat can switch models without a trip to
 * Settings > Models. Switching changes the Conversation job; every profile keeps its own model and settings. */
export function useModelSwitch() {
  const client = useQueryClient()
  const overview = useQuery({ queryKey: KEY, queryFn: () => api<ModelsOverview>('/models') }).data
  const profiles = (overview?.profiles ?? []).filter(profile => profile.ready && !isRecall(profile.config))
  const mix = overview?.mix?.chat
  const { canMix, mixing, mixCount } = mixInfo(mix, profiles)
  const chat = overview?.routes.chat ?? ''
  const turnMix = async (enabled: boolean) => client.setQueryData(KEY, await api<ModelsOverview>('/models/mix', { job: 'chat', ...mix, enabled }, 'PUT'))
  // One model picked: it answers in chat and a Mix stops (its picks are kept, for MIX to turn it back on).
  const choose = async (profileId: string) => {
    if (profileId === MIX) return void await turnMix(true)
    if (mixing) await turnMix(false)
    client.setQueryData(KEY, await api<ModelsOverview>('/models/routes', { job: 'chat', profile_id: profileId }, 'PUT'))
    void client.invalidateQueries({ queryKey: ['connection'] })
  }
  return { profiles, current: mixing ? MIX : chat, choose, canMix, mixCount, ownWorld: !!overview?.world?.own, others: profiles.filter(profile => profile.id !== chat) }
}

/** Up to `count` other profiles to offer after a failed reply, most recently changed first. */
export function alternatives(others: ModelProfile[], count = 2) {
  return [...others].sort((a, b) => (b.updated_at ?? '').localeCompare(a.updated_at ?? '')).slice(0, count)
}
