import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import { useWorkspaceSettings } from '../../companion'
import type { AdultSide, AdultSideChoices, CharacterDefinition, IntimacySetup } from '../../types'
import { Field, TextArea } from '../../components/Fields'
import { useSettled } from './useSettled'

const EMPTY: IntimacySetup = { orientation: '', level: '', drive: '', interests: [], note: '' }

interface Props { definition: () => CharacterDefinition; value: IntimacySetup | null | undefined; set: (change: Partial<CharacterDefinition>) => void }

/** Their adult side (Settings > Realism > Adult side of life): the app rolls it, anything picked here wins. Only shown
 * with the setting on; a sheet that reads as under 18 never gets one. */
export function AdultSideFields(props: Props) {
  return useWorkspaceSettings().data?.adult_side === true ? <AdultSideChoicesFor {...props} /> : null
}

function AdultSideChoicesFor({ definition, value, set }: Props) {
  const body = useSettled({ ...definition(), intimacy: null })
  const found = useQuery({
    queryKey: ['adult-side', body],
    queryFn: () => api<AdultSideChoices>('/companion/adult-side', { definition: body }),
    staleTime: Infinity,
  })
  if (!found.data) return null
  if (!found.data.adult) return <p className="subtle">Adult side: their sheet reads as younger than 18, so they don&apos;t have one.</p>
  const current = { ...EMPTY, ...(value ?? {}) }
  const update = (change: Partial<IntimacySetup>) => {
    const next = { ...current, ...change }
    set({ intimacy: picked(next) || next.note.trim() ? next : null })
  }
  return <AdultSideForm choices={found.data} rolled={found.data.rolled} current={current} update={update} romance={definition().relationship === 'romance'} />
}

interface FormProps { choices: AdultSideChoices; rolled: AdultSide | null; current: IntimacySetup; update: (change: Partial<IntimacySetup>) => void; romance: boolean }

function AdultSideForm({ choices, rolled, current, update, romance }: FormProps) {
  const level = choices.levels.find((entry) => entry.id === (current.level || rolled?.level))
  return (
    <fieldset className="form-stack">
      <legend>Adult side</legend>
      <p className="subtle">Private to them: it only shapes how they act when romance or intimacy comes up. Left as rolled, the app decides.</p>
      <Choice label="Orientation" value={current.orientation} onChange={(orientation) => update({ orientation })}
        rolled={romance ? 'Drawn to you' : rolled?.orientation ?? ''}
        options={choices.orientations.map((id) => ({ id, label: id.charAt(0).toUpperCase() + id.slice(1) }))} />
      <Choice label="How adventurous" value={current.level} onChange={(chosen) => update({ level: chosen })} rolled={rolled?.level_label ?? ''}
        options={choices.levels} hint={level?.text} />
      <Choice label="Drive" value={current.drive} onChange={(drive) => update({ drive })} rolled={rolled?.drive_label ?? ''} options={choices.drives} />
      <Interests choices={choices} rolled={rolled} current={current} update={update} />
      <TextArea label="Anything else" value={current.note} onChange={(note) => update({ note })} maxLength={600} rows={2}
        hint="Optional, in your words. Keep it between consenting adults." />
      {picked(current) && (
        <p><button type="button" className="text-button" onClick={() => update({ ...EMPTY, note: current.note })}>Go back to what was rolled</button></p>
      )}
    </fieldset>
  )
}

/** What they're into: the roll until the user ticks or unticks one, then the user's picks. */
function Interests({ choices, rolled, current, update }: Omit<FormProps, 'romance'>) {
  const own = current.interests.length > 0
  const into = own ? current.interests : rolled?.interests ?? []
  const toggle = (id: string, on: boolean) => update({ interests: on ? [...new Set([...into, id])] : into.filter((entry) => entry !== id) })
  return (
    <Field label="Into" hint={own ? 'Picked by you.' : 'Rolled by the app. Tick or untick to choose your own.'}>
      {(id, describedBy) => (
        <div id={id} className="form-stack" aria-describedby={describedBy}>
          {choices.groups.map((group) => (
            <div key={group.id} className="check-grid" role="group" aria-label={group.label}>
              <strong className="check-grid-heading">{group.label}</strong>
              {choices.interests.filter((entry) => entry.group === group.id).map((entry) => (
                <label key={entry.id}>
                  <input type="checkbox" checked={into.includes(entry.id)} onChange={(event) => toggle(entry.id, event.target.checked)} /> {entry.label}
                </label>
              ))}
            </div>
          ))}
        </div>
      )}
    </Field>
  )
}

function picked(setup: IntimacySetup): boolean {
  return Boolean(setup.orientation || setup.level || setup.drive || setup.interests.length)
}

interface ChoiceProps { label: string; value: string; rolled: string; options: { id: string; label: string }[]; onChange: (value: string) => void; hint?: string }

function Choice({ label, value, rolled, options, onChange, hint }: ChoiceProps) {
  return (
    <Field label={label} hint={hint}>
      {(id, describedBy) => (
        <select id={id} value={value} aria-describedby={describedBy} onChange={(event) => onChange(event.target.value)}>
          <option value="">{rolled ? `As rolled: ${rolled}` : 'As rolled'}</option>
          {options.map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}
        </select>
      )}
    </Field>
  )
}
