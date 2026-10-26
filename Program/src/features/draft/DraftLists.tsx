import { useContext, useEffect, useRef, type ReactNode } from 'react'
import { ChevronDown, Dices, LoaderCircle, Plus, Trash2, Undo2, WandSparkles } from 'lucide-react'
import { Field, TextArea, TextInput } from '../../components/Fields'
import { COLOUR_KINDS, hoodNames, MONTHS, PLACE_KINDS, POLISHED, TRANSIT_KINDS, type Definition, type Item, type ListKey, type Section } from './draftText'
import { PolishContext } from './polishContext'

/** What a list needs from the table: change or remove one of its items, redraw it, and which item is open. */
export interface ListProps {
  definition: Definition
  open: string | null
  onOpen: (id: string | null) => void
  onChange: (key: ListKey, id: string, change: Partial<Item>) => void
  onRemove: (key: ListKey, item: Item) => void
  onRoll?: (section: Section) => void
}

/** A list's heading, its count and Roll again, which redraws just that list. */
export function ListHead({ title, count, hint, section, onRoll, children }: { title: string; count: number; hint: string; section: Section; onRoll?: (section: Section) => void; children?: ReactNode }) {
  const id = `draft-${section}`
  return (
    <header className="draft-list-head">
      <div>
        <h2 id={id}>{title} <span className="subtle">{count}</span></h2>
        <p className="subtle">{hint}</p>
        <PolishNote section={section} />
      </div>
      <div className="draft-list-actions">
        {children}
        {onRoll && <button type="button" className="button" onClick={() => onRoll(section)}><Dices aria-hidden="true" />Roll again</button>}
        <PolishButton section={section} />
      </div>
    </header>
  )
}

const POLISH_SAYS = "Polish uses your text model to rewrite names and blurbs. Rows you've changed are left alone."
const NO_MODEL = 'Set up a text model in Companion first, under Settings > Models.'

/** Rewrites the list's names and summaries in the place's voice with the user's text model. */
function PolishButton({ section }: { section: Section }) {
  const polish = useContext(PolishContext)
  if (!polish || !POLISHED[section]) return null
  const here = polish.polishing === section
  const off = polish.polishing !== null || polish.ready !== true
  return (
    <button type="button" className="button" aria-disabled={off} title={polish.ready === false ? NO_MODEL : POLISH_SAYS} aria-describedby={`draft-polish-${section}`}
      onClick={() => { if (!off) polish.polish(section) }}>
      {here ? <LoaderCircle aria-hidden="true" className="spin" /> : <WandSparkles aria-hidden="true" />}{here ? 'Polishing…' : 'Polish'}
    </button>
  )
}

/** Under the list's hint: what Polish does (or what it needs), and Undo polish until the next change. */
function PolishNote({ section }: { section: Section }) {
  const polish = useContext(PolishContext)
  if (!polish || !POLISHED[section]) return null
  return <>
    <p className="subtle draft-polish-note" id={`draft-polish-${section}`}>{polish.ready === false ? NO_MODEL : POLISH_SAYS}</p>
    {polish.undoable === section && <button type="button" className="text-button draft-undo-polish" onClick={polish.undo}><Undo2 aria-hidden="true" />Undo polish</button>}
  </>
}

/** One item: its name and what it is, opening to its fields. The open item scrolls into view, as when picked on the map. */
export function ItemRow({ item, meta, open, onOpen, onRemove, children }: { item: Item; meta: string; open: boolean; onOpen: (id: string | null) => void; onRemove: () => void; children: ReactNode }) {
  const row = useRef<HTMLLIElement>(null)
  useEffect(() => { if (open) row.current?.scrollIntoView({ block: 'nearest' }) }, [open])
  const panel = `draft-item-${item.id}`
  const polished = useContext(PolishContext)?.polished.has(item.id)
  return (
    <li ref={row} className={`draft-item${open ? ' open' : ''}`}>
      <button type="button" className="draft-item-head" aria-expanded={open} aria-controls={panel} onClick={() => onOpen(open ? null : item.id)}>
        <span className="draft-item-name">{item.name || 'Unnamed'}</span>
        {polished && <span className="draft-tag">Polished</span>}
        <span className="subtle draft-item-meta">{meta}</span>
        <ChevronDown aria-hidden="true" className="draft-item-chevron" />
      </button>
      {open && <div id={panel} className="draft-item-body form-stack">
        {children}
        <div className="form-actions"><button type="button" className="text-button" onClick={onRemove}><Trash2 aria-hidden="true" />Remove</button></div>
      </div>}
    </li>
  )
}

/** The fields every item has. */
export function NameAndSummary({ item, onChange }: { item: Item; onChange: (change: Partial<Item>) => void }) {
  return <>
    <TextInput label="Name" value={item.name} maxLength={120} onChange={(name) => onChange({ name })} />
    <TextArea label="What it is" value={item.summary} maxLength={400} rows={3} onChange={(summary) => onChange({ summary })} />
  </>
}

export function Choice({ label, value, options, onChange, hint }: { label: string; value: string; options: Record<string, string>; onChange: (value: string) => void; hint?: string }) {
  // A kind the city file has that the list does not name stays choosable.
  const shown = value in options || !value ? options : { [value]: value, ...options }
  return (
    <Field label={label} hint={hint}>
      {(id, describedBy) => <select id={id} value={value} aria-describedby={describedBy} onChange={(event) => onChange(event.target.value)}>
        {Object.entries(shown).map(([key, text]) => <option key={key} value={key}>{text}</option>)}
      </select>}
    </Field>
  )
}

/** Places, by neighbourhood, each with Add a place. */
export function PlaceList({ definition, open, onOpen, onChange, onRemove, onRoll, onAdd }: ListProps & { onAdd: (hood: string) => void }) {
  const hoods = hoodNames(definition)
  const word = definition.enclosed ? 'deck' : 'neighborhood'
  return (
    <section className="draft-list" aria-labelledby="draft-places">
      <ListHead title="Places" count={definition.places.length} section="places" onRoll={onRoll} hint={`Where people eat, drink, shop and spend their days. Each ${word} needs somewhere to eat or drink.`} />
      {definition.neighborhoods.map((hood) => (
        <div key={hood.id} className="draft-group">
          <h3>{hood.name}</h3>
          <ul className="draft-items">
            {definition.places.filter((item) => item.neighborhood === hood.id).map((item) => (
              <ItemRow key={item.id} item={item} meta={PLACE_KINDS[item.kind ?? ''] ?? item.kind ?? ''} open={open === item.id} onOpen={onOpen} onRemove={() => onRemove('places', item)}>
                <NameAndSummary item={item} onChange={(change) => onChange('places', item.id, change)} />
                <div className="draft-pair">
                  <Choice label="Kind of place" value={item.kind ?? ''} options={PLACE_KINDS} onChange={(kind) => onChange('places', item.id, { kind })} />
                  <Choice label={word === 'deck' ? 'Deck' : 'Neighborhood'} value={item.neighborhood ?? ''} options={hoods} onChange={(neighborhood) => onChange('places', item.id, { neighborhood })} />
                </div>
              </ItemRow>
            ))}
          </ul>
          <button type="button" className="text-button draft-add" onClick={() => onAdd(hood.id)}><Plus aria-hidden="true" />Add a place in {hood.name}</button>
        </div>
      ))}
    </section>
  )
}

export function HoodList({ definition, open, onOpen, onChange, onRemove, onRoll, onAdd }: ListProps & { onAdd: () => void }) {
  const ship = definition.enclosed === true
  return (
    <section className="draft-list" aria-labelledby="draft-hoods">
      <ListHead title={ship ? 'Decks' : 'Neighborhoods'} count={definition.neighborhoods.length} section="hoods" onRoll={onRoll}
        hint={ship ? 'The decks of the ship. Rolling them again draws up the whole ship again.' : 'The parts of town. Rolling them again draws up the whole place again.'} />
      <ul className="draft-items">
        {definition.neighborhoods.map((hood) => {
          const count = definition.places.filter((item) => item.neighborhood === hood.id).length
          return (
            <ItemRow key={hood.id} item={hood} meta={`${count} ${count === 1 ? 'place' : 'places'}`} open={open === hood.id} onOpen={onOpen} onRemove={() => onRemove('neighborhoods', hood)}>
              <NameAndSummary item={hood} onChange={(change) => onChange('neighborhoods', hood.id, change)} />
            </ItemRow>
          )
        })}
      </ul>
      <button type="button" className="text-button draft-add" onClick={onAdd}><Plus aria-hidden="true" />Add {ship ? 'a deck' : 'a neighborhood'}</button>
    </section>
  )
}

export function WorkList({ definition, open, onOpen, onChange, onRemove, onRoll }: ListProps) {
  const hoods = hoodNames(definition)
  return (
    <section className="draft-list draft-list-work" aria-labelledby="draft-employers">
      <ListHead title="Work" count={definition.employers.length} section="employers" onRoll={onRoll} hint="Employers, and the jobs of the era they hire for. A companion who lives here can work at one." />
      <ul className="draft-items">
        {definition.employers.map((item) => (
          <ItemRow key={item.id} item={item} meta={hoods[item.neighborhood ?? ''] ?? ''} open={open === item.id} onOpen={onOpen} onRemove={() => onRemove('employers', item)}>
            <NameAndSummary item={item} onChange={(change) => onChange('employers', item.id, change)} />
            <Choice label={definition.enclosed ? 'Deck' : 'Neighborhood'} value={item.neighborhood ?? ''} options={hoods} onChange={(neighborhood) => onChange('employers', item.id, { neighborhood })} />
          </ItemRow>
        ))}
      </ul>
    </section>
  )
}

export function TransitList({ definition, open, onOpen, onChange, onRemove, onRoll }: ListProps) {
  return (
    <section className="draft-list" aria-labelledby="draft-transit">
      <ListHead title="Getting about" count={definition.transit.length} section="transit" onRoll={onRoll} hint="How people get from one part of town to another, and how long it takes them." />
      <ul className="draft-items">
        {definition.transit.map((item) => (
          <ItemRow key={item.id} item={item} meta={TRANSIT_KINDS[item.kind ?? ''] ?? item.kind ?? ''} open={open === item.id} onOpen={onOpen} onRemove={() => onRemove('transit', item)}>
            <NameAndSummary item={item} onChange={(change) => onChange('transit', item.id, change)} />
            <Choice label="Kind" value={item.kind ?? ''} options={TRANSIT_KINDS} onChange={(kind) => onChange('transit', item.id, { kind })} />
          </ItemRow>
        ))}
      </ul>
    </section>
  )
}

export function EventList({ definition, open, onOpen, onChange, onRemove, onRoll }: ListProps) {
  const hoods = { '': definition.enclosed ? 'All over the ship' : 'All over town', ...hoodNames(definition) }
  return (
    <section className="draft-list" aria-labelledby="draft-events">
      <ListHead title="Events" count={definition.annual_events.length} section="events" onRoll={onRoll} hint="What happens here every year, and when." />
      <ul className="draft-items">
        {definition.annual_events.map((item) => (
          <ItemRow key={item.id} item={item} meta={item.months.map((month) => MONTHS[month - 1]).join(', ')} open={open === item.id} onOpen={onOpen} onRemove={() => onRemove('annual_events', item)}>
            <NameAndSummary item={item} onChange={(change) => onChange('annual_events', item.id, change)} />
            <Months value={item.months} onChange={(months) => onChange('annual_events', item.id, { months })} />
            <Choice label="Where" value={item.neighborhood ?? ''} options={hoods} onChange={(neighborhood) => onChange('annual_events', item.id, { neighborhood: neighborhood || undefined })} />
          </ItemRow>
        ))}
      </ul>
    </section>
  )
}

/** Months as toggles; the last one cannot be turned off, since an event happens in at least one. */
function Months({ value, onChange }: { value: number[]; onChange: (months: number[]) => void }) {
  const flip = (month: number) => onChange(value.includes(month) ? value.filter((item) => item !== month) : [...value, month].sort((a, b) => a - b))
  return (
    <fieldset className="draft-months">
      <legend>Months</legend>
      <div className="vibe-picks">
        {MONTHS.map((name, index) => {
          const on = value.includes(index + 1)
          return <button key={name} type="button" className="vibe-pick" aria-pressed={on} disabled={on && value.length === 1} onClick={() => flip(index + 1)}>{name}</button>
        })}
      </div>
    </fieldset>
  )
}

export function ColourList({ definition, open, onOpen, onChange, onRemove, onRoll }: ListProps) {
  return (
    <section className="draft-list" aria-labelledby="draft-colour">
      <ListHead title="Local color" count={definition.local_color.length} section="colour" onRoll={onRoll} hint="What locals eat, drink, say and tell each other, so a companion can bring it up." />
      <ul className="draft-items">
        {definition.local_color.map((item) => (
          <ItemRow key={item.id} item={item} meta={COLOUR_KINDS[item.kind ?? ''] ?? item.kind ?? ''} open={open === item.id} onOpen={onOpen} onRemove={() => onRemove('local_color', item)}>
            <NameAndSummary item={item} onChange={(change) => onChange('local_color', item.id, change)} />
            <Choice label="Kind" value={item.kind ?? ''} options={COLOUR_KINDS} onChange={(kind) => onChange('local_color', item.id, { kind })} />
          </ItemRow>
        ))}
      </ul>
    </section>
  )
}
