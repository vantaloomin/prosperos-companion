import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { Backstory, UntoldPair } from '../../types'
import { PAIR_STAGES } from '../memories/pairText'

/**
 * How two companions know each other, told once, the first time they share a group: a starting stage and a line
 * of backstory, both optional. After that only what happens between them moves it (companion/memory/pairs.py).
 */
export function Backstories({ companionIds, value, onChange }: { companionIds: string[]; value: Backstory[]; onChange: (value: Backstory[]) => void }) {
  const ids = [...companionIds].sort()
  const untold = useQuery({ queryKey: ['groups-untold', ids], enabled: ids.length >= 2,
    queryFn: () => api<{ pairs: UntoldPair[] }>('/groups/untold', { companion_ids: ids }) })
  const pairs = ids.length >= 2 ? untold.data?.pairs ?? [] : []
  if (!pairs.length) return null
  const told = (pair: UntoldPair) => value.find((item) => item.a === pair.a && item.b === pair.b) ?? { a: pair.a, b: pair.b, level: null, how: pair.how }
  const set = (pair: UntoldPair, change: Partial<Backstory>) => {
    const next = { ...told(pair), ...change }
    onChange([...value.filter((item) => !(item.a === pair.a && item.b === pair.b)), next])
  }
  return (
    <fieldset className="group-backstories">
      <legend>How they know each other</legend>
      <p className="subtle">Filled in from where they live and whether they have met. Change it now if you like: after they first share a group, only what happens between them changes it.</p>
      {pairs.map((pair) => {
        const current = told(pair)
        const label = `${pair.a_name.split(' ')[0]} and ${pair.b_name.split(' ')[0]}`
        return (
          <div key={`${pair.a}-${pair.b}`} className="group-backstory">
            <label>{label}
              <select value={current.level ?? ''} onChange={(event) => set(pair, { level: event.target.value ? Number(event.target.value) : null })}>
                <option value="">{PAIR_STAGES[pair.level - 1]} (as things stand)</option>
                {PAIR_STAGES.map((stage, index) => <option key={stage} value={index + 1}>{stage}</option>)}
              </select>
            </label>
            <input aria-label={`How ${label} know each other`} value={current.how} maxLength={300} placeholder="e.g. Roommates in college"
              onChange={(event) => set(pair, { how: event.target.value })} />
          </div>
        )
      })}
    </fieldset>
  )
}
