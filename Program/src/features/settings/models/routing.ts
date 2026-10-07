import type { ModelsOverview } from './types.ts'

/** What a job's selector shows: its own profile, or the conversation profile it falls back to. */
export function jobChoice(overview: ModelsOverview, job: string): { value: string; inherited: string | null } {
  const own = overview.routes[job] ?? ''
  const chat = overview.profiles.find(profile => profile.id === overview.routes.chat)
  return { value: own, inherited: job === 'chat' || own ? null : chat?.name ?? null }
}

/** What recall does with no profile of its own: the conversation profile's embeddings if it has them, else keywords. */
export function recallFallback(overview: ModelsOverview): string {
  const chat = overview.profiles.find(profile => profile.id === overview.routes.chat)
  return chat?.recall_ready ? `Same as conversation (${chat.name})` : 'Keywords only'
}
