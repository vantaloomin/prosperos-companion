/** A new companion's picks and form, kept while the user steps away (to Settings, say) and comes back, and through
 * a reload. Held for this tab and this world only; they go once the companion is created. */
import { useEffect, useState } from 'react'
import type { DraftRequest, FormState } from './drafting'
import type { Start } from './Character'
import { useWorlds } from '../worlds/useWorlds'

const KEY = 'companion:new-companion'

interface Parts { picks: { request: DraftRequest; cityPicked: boolean }; start: Start | null; form: FormState }
type Kept = Partial<Parts> & { world: string | null }

function read(world: string | null): Kept | null {
  try {
    const kept = JSON.parse(sessionStorage.getItem(KEY) ?? 'null') as Kept | null
    return kept && (!kept.world || !world || kept.world === world) ? kept : null
  } catch { return null }
}

function write(world: string | null, change: Partial<Parts>) {
  try { sessionStorage.setItem(KEY, JSON.stringify({ ...read(world), ...change, world })) } catch { /* Kept for this page only. */ }
}

/** Forget one part (a new draft replaces the form), or everything once the companion exists. */
export function forgetDraft(part?: keyof Parts) {
  try {
    if (!part) { sessionStorage.removeItem(KEY); return }
    const kept = JSON.parse(sessionStorage.getItem(KEY) ?? 'null') as Kept | null
    if (kept) { delete kept[part]; sessionStorage.setItem(KEY, JSON.stringify(kept)) }
  } catch { /* Nothing kept. */ }
}

/** useState that starts from the kept part and keeps every change, while `keep` is on. */
export function useKept<K extends keyof Parts>(part: K, initial: () => Parts[K], keep = true) {
  const world = useWorlds().data?.active_world_id ?? null
  const [value, setValue] = useState<Parts[K]>(() => {
    const kept = keep ? read(world)?.[part] : undefined
    return kept === undefined ? initial() : kept as Parts[K]
  })
  useEffect(() => { if (keep) write(world, { [part]: value }) }, [keep, world, part, value])
  return [value, setValue] as const
}
