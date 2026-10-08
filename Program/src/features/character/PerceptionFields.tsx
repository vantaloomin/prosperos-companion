import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { CharacterDefinition } from '../../types'
import { Field } from '../../components/Fields'

/** Bank picks that fit the sheet's words (companion/world/perception.py), and what an empty field uses once saved. */
export interface PerceptionSuggestions {
  automatic: { seen_as: string; sees_self: string } | null
  seen_as: string[]
  sees_self: string[]
}

interface Props { definition: () => CharacterDefinition; seenAs: string; seesSelf: string; set: (change: Partial<CharacterDefinition>) => void }

/** "How others see them" and "How they see themselves": optional, each free text or a pick from the bank. */
export function PerceptionFields({ definition, seenAs, seesSelf, set }: Props) {
  // Their own two fields never change what fits, so typing in them asks for nothing.
  const body = useSettled({ ...definition(), seen_as: '', sees_self: '' })
  const found = useQuery({
    queryKey: ['perception', body],
    queryFn: () => api<PerceptionSuggestions>('/companion/perception', { definition: body }),
    staleTime: Infinity,
  })
  const automatic = found.data?.automatic
  return (
    <>
      <Pickable label="How others see them" value={seenAs} rows={2} maxLength={400} options={found.data?.seen_as ?? []}
        onChange={(seen_as) => set({ seen_as })}
        placeholder={automatic ? `Left empty: ${automatic.seen_as}` : 'Left empty, the app picks one that fits the rest of their sheet.'}
        hint="Optional. How they come across to everyone else: a trait, a habit people notice, what sets them off. Other people in a group chat see this line." />
      <Pickable label="How they see themselves" value={seesSelf} rows={4} maxLength={1200} options={found.data?.sees_self ?? []}
        onChange={(sees_self) => set({ sees_self })}
        placeholder={automatic ? `Left empty:\n${automatic.sees_self}` : 'Left empty, the app picks lines that fit the rest of their sheet.'}
        hint="Optional and private: only they know it. A few lines in their own voice, one per line. It can differ from how others see them." />
    </>
  )
}

interface PickableProps { label: string; value: string; rows: number; maxLength: number; options: string[]; onChange: (value: string) => void; placeholder: string; hint: string }

function Pickable({ label, value, rows, maxLength, options, onChange, placeholder, hint }: PickableProps) {
  return (
    <Field label={label} hint={hint}>
      {(id, describedBy) => (
        <div className="perception-field">
          <textarea id={id} rows={rows} value={value} maxLength={maxLength} placeholder={placeholder} aria-describedby={describedBy} onChange={(event) => onChange(event.target.value)} />
          {options.length > 0 && (
            <select aria-label={`Pick ${label.toLowerCase()}`} value="" onChange={(event) => { if (event.target.value) onChange(event.target.value) }}>
              <option value="">Pick one that fits…</option>
              {options.map((option) => <option key={option} value={option}>{option.split('\n')[0]}{option.includes('\n') ? ' …' : ''}</option>)}
            </select>
          )}
        </div>
      )}
    </Field>
  )
}

/** The sheet once typing pauses, so suggestions follow the form without a request per keystroke. */
function useSettled(value: CharacterDefinition, delay = 600): CharacterDefinition {
  const [settled, setSettled] = useState(value)
  const key = JSON.stringify(value)
  useEffect(() => {
    const timer = window.setTimeout(() => setSettled(JSON.parse(key) as CharacterDefinition), delay)
    return () => window.clearTimeout(timer)
  }, [key, delay])
  return settled
}
