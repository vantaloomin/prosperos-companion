import { useState } from 'react'
import { Plus, X } from 'lucide-react'
import { Field } from '../../components/Fields'
import { asChip } from './ownWordsText'

const MOST = 8

interface Box { id: string; label: string }

interface Props {
  label: string; hint: string; placeholder: string; value: string[]; onChange: (value: string[]) => void
  /** The other list ("Not into" for "Also into"): the same words can't be in both. */
  other: { label: string; value: string[] }
  /** Boxes in the lists above: typing one ticks it instead of adding a chip. */
  boxes?: Box[]; onBox?: (id: string) => void
  outlined?: boolean
}

/** A short list in the user's own words (their own turn-ons or turn-offs on the Adult side): type one, add it, take
 * it off with its X. Enter adds too. Iris: chips read mid-sentence, so a first capital goes unless it looks like a
 * name; a repeat is left out quietly; words already in the other list are refused with a line saying so. */
export function OwnWords({ label, hint, placeholder, value, onChange, other, boxes = [], onBox, outlined }: Props) {
  const [draft, setDraft] = useState('')
  const text = asChip(draft)
  const same = (entry: string) => entry.toLowerCase() === text.toLowerCase()
  const clash = text !== '' && other.value.some(same)
  const full = value.length >= MOST
  const add = () => {
    if (!text || clash || full) return
    const box = boxes.find((entry) => same(entry.label))
    if (box && onBox) onBox(box.id)
    else if (!value.some(same)) onChange([...value, text])
    setDraft('')
  }
  const shown = full ? `That's ${MOST}. Remove one to add another.` : clash ? `That's already in ${other.label}.` : hint
  return (
    <Field label={label} hint={shown}>
      {(id, describedBy) => (<div className="own-words">
        {value.length > 0 && <ul className={`moment-chips${outlined ? ' chips-outlined' : ''}`} aria-label={label}>
          {value.map((entry) => (
            <li key={entry}>
              {entry}
              <button type="button" className="moment-remove" aria-label={`Take off ${entry}`}
                onClick={() => onChange(value.filter((kept) => kept !== entry))}><X aria-hidden="true" /></button>
            </li>
          ))}
        </ul>}
        <div className="own-words-add">
          <input id={id} value={draft} maxLength={80} placeholder={placeholder} aria-describedby={describedBy} disabled={full}
            aria-invalid={clash || undefined} onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); add() } }} />
          <button type="button" className="button" disabled={!text || clash || full} onClick={add}><Plus aria-hidden="true" />Add</button>
        </div>
      </div>)}
    </Field>
  )
}
