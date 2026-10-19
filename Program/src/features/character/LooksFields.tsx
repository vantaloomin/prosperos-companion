import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import type { CharacterDefinition, Looks } from '../../types'
import { Field, Toggle } from '../../components/Fields'
import { useSettled } from './useSettled'
import { decadeHint, emptyLooks, emptyText, heightLabel, keepsAgeHint, looksWords, numberChoices, weightLabel, type LooksWord } from './looksText'

/** What each empty field uses once saved (companion/world/looks.py), and suggestions for the word fields. */
interface LooksSuggestions { automatic: Looks | null; covered?: string[]; options: Partial<Record<LooksWord, string[]>>; age_now?: number | null }

interface Props { definition: () => CharacterDefinition; looks: Looks | undefined; set: (change: Partial<CharacterDefinition>) => void }

/** Face shape, height, build and the rest, so every picture shows the same person. Each is optional: left empty, the app draws it. */
export function LooksFields({ definition, looks, set }: Props) {
  const current = { ...emptyLooks(), ...looks }
  // What is drawn follows who they are (pronouns, heritage, the appearance text), and a drawn build or weight follows the height, weight or build set here.
  const body = useSettled({ ...definition(), looks: current })
  const found = useQuery({
    queryKey: ['looks', body],
    queryFn: () => api<LooksSuggestions>('/companion/looks', { definition: body }),
    staleTime: Infinity,
  })
  const automatic = found.data?.automatic ?? null
  const change = (field: keyof Looks, value: string | number | null) => set({ looks: { ...current, [field]: value } })
  const covered = coveredBy(found.data)
  const left = (shown: string | null, field: keyof Looks) => emptyText(automatic !== null, covered.has(field), shown)
  return (
    <fieldset className="form-stack">
      <legend>Looks</legend>
      <small className="subtle">Pictures of them use these, so they look like the same person every time. Leave any field empty and the app picks one that fits; where Appearance already says it, Appearance wins.</small>
      <div className="form-grid">
        <NumberChoice label="Age" value={current.age} choices={numberChoices('age')} format={(age) => `${age}`} empty={left(automatic?.age ? `${automatic.age}` : null, 'age')} onChange={(value) => change('age', value)} />
        <NumberChoice label="Height" value={current.height_cm} choices={numberChoices('height')} format={heightLabel} empty={left(automatic?.height_cm ? heightLabel(automatic.height_cm) : null, 'height_cm')} onChange={(value) => change('height_cm', value)} />
        <NumberChoice label="Weight" value={current.weight_kg} choices={numberChoices('weight')} format={weightLabel} empty={left(automatic?.weight_kg ? weightLabel(automatic.weight_kg) : null, 'weight_kg')} onChange={(value) => change('weight_kg', value)} />
        {looksWords.map(({ field, label }) => (
          <WordField key={field} field={field} label={label} value={current[field]} options={found.data?.options[field] ?? []}
            empty={left(automatic?.[field] || null, field)} onChange={(value) => change(field, value)} />
        ))}
      </div>
      <KeepsAge definition={definition()} written={current.age} found={found.data} set={set} />
    </fieldset>
  )
}

interface ChoiceProps { label: string; value: number | null; choices: number[]; format: (value: number) => string; empty: string; onChange: (value: number | null) => void }

/** A bounded number from a list, with "left empty" first so the app's pick stays the default. */
function NumberChoice({ label, value, choices, format, empty, onChange }: ChoiceProps) {
  const listed = value !== null && !choices.includes(value) ? [...choices, value].sort((a, b) => a - b) : choices
  return <Field label={label}>{(id) => (
    <select id={id} value={value ?? ''} onChange={(event) => onChange(event.target.value ? Number(event.target.value) : null)}>
      <option value="">{empty}</option>
      {listed.map((choice) => <option key={choice} value={choice}>{format(choice)}</option>)}
    </select>
  )}</Field>
}

interface WordProps { field: LooksWord; label: string; value: string; options: string[]; empty: string; onChange: (value: string) => void }

/** A word field, free text with the bank's suggestions offered as you type. */
function WordField({ field, label, value, options, empty, onChange }: WordProps) {
  return <Field label={label}>{(id) => <>
    <input id={id} value={value} maxLength={field === 'hair' || field === 'feature' ? 200 : 120} list={options.length ? `looks-${field}` : undefined}
      placeholder={empty} onChange={(event) => onChange(event.target.value)} />
    {options.length > 0 && <datalist id={`looks-${field}`}>{options.map((option) => <option key={option} value={option} />)}</datalist>}
  </>}</Field>
}

function coveredBy(found: LooksSuggestions | undefined) {
  return new Set(found?.covered ?? [])
}

interface KeepsAgeProps { definition: CharacterDefinition; written: number | null; found: LooksSuggestions | undefined; set: Props['set'] }

/** The "Keeps their age" lock, off by default: they turn a year older on each birthday unless it is on. */
function KeepsAge({ definition, written, found, set }: KeepsAgeProps) {
  return <Toggle label="Keeps their age" checked={Boolean(definition.keeps_age)} onChange={(keeps_age) => set({ keeps_age })}
    hint={[keepsAgeHint(definition, written ?? found?.automatic?.age ?? null, found?.age_now ?? null),
      decadeHint(definition.identity ?? '', found?.age_now ?? null)].filter(Boolean).join(' ')} />
}
