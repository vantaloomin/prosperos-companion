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

/** Folded by default (Iris): it is private and long, and the form may be scrolled with someone nearby. The summary
 * says whether it is as rolled or how many things the user changed. */
function AdultSideForm({ choices, rolled, current, update, romance }: FormProps) {
  return (
    <details className="adult-side">
      <summary>Adult side · {changesText(changed(current))}</summary>
      <div className="form-stack">
        <p className="subtle">Private to them: it only shapes how they act when romance or intimacy comes up. Left as rolled, the app decides.</p>
        <Selects choices={choices} rolled={rolled} current={current} update={update} romance={romance} />
        <Interests choices={choices} rolled={rolled} current={current} update={update} />
        <TextArea label="Anything else" value={current.note} onChange={(note) => update({ note })} maxLength={600} rows={2}
          hint="Optional, in your words. Keep it between consenting adults." />
        {picked(current) && (
          <p><button type="button" className="text-button" onClick={() => update({ ...EMPTY, note: current.note })}>Go back to what was rolled</button></p>
        )}
      </div>
    </details>
  )
}

/** Orientation, how adventurous and drive, each "As rolled" until the user picks one. */
function Selects({ choices, rolled, current, update, romance }: FormProps) {
  const level = choices.levels.find((entry) => entry.id === (current.level || rolled?.level))
  const drive = choices.drives.find((entry) => entry.id === (current.drive || rolled?.drive))
  return (<>
    <Choice label="Orientation" value={current.orientation} onChange={(orientation) => update({ orientation })}
      rolled={romance ? 'Drawn to you' : capital(rolled?.orientation ?? '')}
      options={choices.orientations.map((id) => ({ id, label: capital(id) }))} />
    <Choice label="How adventurous" value={current.level} onChange={(chosen) => update({ level: chosen })} rolled={rolled?.level_label ?? ''}
      options={choices.levels} hint={level?.text} />
    <Choice label="Drive" value={current.drive} onChange={(chosen) => update({ drive: chosen })} rolled={rolled?.drive_label ?? ''}
      options={choices.drives} hint={drive?.text} />
  </>)
}

function changesText(count: number): string {
  if (!count) return 'As rolled'
  return `${count} ${count === 1 ? 'change' : 'changes'}`
}

/** What they're into: the roll until the user ticks or unticks one, then the user's picks. One line says what they
 * are into; each group folds, open when it holds a pick. */
function Interests({ choices, rolled, current, update }: Omit<FormProps, 'romance'>) {
  const own = current.interests.length > 0
  const into = own ? current.interests : rolled?.interests ?? []
  const toggle = (id: string, on: boolean) => update({ interests: on ? [...new Set([...into, id])] : into.filter((entry) => entry !== id) })
  const labels = choices.interests.filter((entry) => into.includes(entry.id)).map((entry) => entry.label.toLowerCase())
  return (
    <div className="form-stack">
      <div>
        <strong>Into: {labels.length ? labels.join(', ') : 'Nothing yet'}</strong>
        <p className="subtle">
          {own ? 'Picked by you.' : 'Rolled by the app. Tick or untick to choose your own.'}
          {own && <>{' '}<button type="button" className="text-button" onClick={() => update({ interests: [] })}>Back to as rolled</button></>}
        </p>
      </div>
      {choices.groups.map((group) => {
        const entries = choices.interests.filter((entry) => entry.group === group.id)
        const count = entries.filter((entry) => into.includes(entry.id)).length
        return (
          <details key={group.id} className="interest-group" open={count > 0}>
            <summary>{group.label} · {count}</summary>
            <div className="check-grid" role="group" aria-label={group.label}>
              {entries.map((entry) => (
                <label key={entry.id}>
                  <input type="checkbox" checked={into.includes(entry.id)} onChange={(event) => toggle(entry.id, event.target.checked)} /> {entry.label}
                </label>
              ))}
            </div>
          </details>
        )
      })}
    </div>
  )
}

function picked(setup: IntimacySetup): boolean {
  return Boolean(setup.orientation || setup.level || setup.drive || setup.interests.length)
}

/** How many things the user set rather than left as rolled. */
function changed(setup: IntimacySetup): number {
  return [setup.orientation, setup.level, setup.drive, setup.interests.length, setup.note.trim()].filter(Boolean).length
}

function capital(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1)
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
