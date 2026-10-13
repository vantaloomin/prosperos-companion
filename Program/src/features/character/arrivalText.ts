import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { CitySummary, World } from '../../types'
import { useWorlds } from '../worlds/useWorlds'
import { personaName } from '../worlds/worldsText'

export interface Arrival { city: string; persona: string; previous?: World }

/** A world after the first, still without a companion: the user just arrived there (Iris), so the welcome says
 * where they are instead of reading like a first install. Null in the first world. */
export function useArrival(): Arrival | null {
  const worlds = useWorlds().data
  const cities = useQuery({ queryKey: ['cities'], queryFn: () => api<CitySummary[]>('/world/cities'), staleTime: Infinity })
  if (!worlds || worlds.world.first) return null
  const city = cities.data?.find((item) => item.id === worlds.world.city_id)?.name ?? worlds.world.name
  const others = worlds.personas.flatMap((persona) => persona.worlds).filter((world) => !world.active)
  const previous = others.sort((a, b) => b.used_at.localeCompare(a.used_at))[0]
  return { city, persona: personaName(worlds.persona), previous }
}

export function arrivalLede({ city, persona }: Arrival): string {
  const who = persona ? `You're ${persona} in ${city} now.` : `You're in ${city} now.`
  return `${who} Make your first companion here. Your settings and models came with you.`
}

