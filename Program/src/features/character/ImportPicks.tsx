import { useId, useState } from 'react'
import { anythingTicked, characterLines, tickBook, entryCount, entryHint, mapCounts, pictureHint, owners, startingPicks, type CharacterFile, type FileContents, type MapFile, type Picks, type PreviewBook } from './importPicksText'

interface Props { filename: string; found: FileContents; busy: boolean; onImport: (picks: Picks) => void; onCancel: () => void }

/** What a file holds, every part ticked, with Import and Cancel. Unticking a part leaves it out. */
export function ImportPicks({ filename, found, busy, onImport, onCancel }: Props) {
  const [picks, setPicks] = useState(() => startingPicks(found))
  const change = (next: Partial<Picks>) => setPicks((current) => ({ ...current, ...next }))
  const headingId = useId()
  return (
    <div className="import-picks" role="group" aria-labelledby={headingId}>
      <div>
        <h3 id={headingId}>In {filename}</h3>
        <p className="subtle">{found.format}. Everything in it is ticked; untick anything you&rsquo;d rather leave out.</p>
      </div>
      <ul className="import-parts">
        {found.kind === 'map' ? <CityPart found={found} picks={picks} change={change} /> : <CharacterPart found={found} picks={picks} change={change} />}
        {found.book && <BookPart found={found} book={found.book} picks={picks} change={change} />}
      </ul>
      {found.kind === 'character' && found.unused.length > 0 && <p className="subtle">Not brought over: {found.unused.join(', ')}. They set up someone else&rsquo;s story, and here their life starts in town.</p>}
      <div className="form-actions wrap">
        <button type="button" className="button primary" disabled={busy || !anythingTicked(found, picks)} onClick={() => onImport(picks)}>{busy ? 'Importing…' : 'Import'}</button>
        <button type="button" className="button" disabled={busy} onClick={onCancel}>Cancel</button>
        {!anythingTicked(found, picks) && <span className="subtle">Tick something to import.</span>}
      </div>
    </div>
  )
}

interface PartProps<T> { found: T; picks: Picks; change: (next: Partial<Picks>) => void }

function Check({ checked, disabled, onChange, label, hint }: { checked: boolean; disabled?: boolean; onChange: (checked: boolean) => void; label: string; hint?: string }) {
  return (
    <label className="checkbox-row">
      <input type="checkbox" checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} />
      <span><span className="import-part-name">{label}</span>{hint && <small>{hint}</small>}</span>
    </label>
  )
}

function CharacterPart({ found, picks, change }: PartProps<CharacterFile>) {
  if (!found.character) return null
  const { name, hint, about } = characterLines(found, found.character)
  return (
    <li>
      <Check checked={picks.main} onChange={(main) => change({ main, loreFor: '' })} label={name} hint={hint} />
      {about && <p className="import-about subtle">{about}</p>}
      {found.picture && <PicturePart picture={found.picture} picks={picks} change={change} />}
    </li>
  )
}

function PicturePart({ picture, picks, change }: { picture: NonNullable<CharacterFile['picture']>; picks: Picks; change: (next: Partial<Picks>) => void }) {
  return (
    <div className="import-nested">
      <Check checked={picks.main && picks.picture && picture.usable} disabled={!picks.main || !picture.usable} onChange={(ticked) => change({ picture: ticked })}
        label="Their picture" hint={pictureHint(picture)} />
    </div>
  )
}

function CityPart({ found, picks, change }: PartProps<MapFile>) {
  const hint = found.already ? `This map already came in as ${found.already}, so the city can't come in twice.` : `A new city in Settings > Life & cities, with ${mapCounts(found)}.`
  return <li><Check checked={picks.main && !found.already} disabled={!!found.already} onChange={(main) => change({ main })} label={`The city, ${found.city.name}`} hint={hint} /></li>
}

function BookPart({ found, book, picks, change }: PartProps<FileContents> & { book: PreviewBook }) {
  const label = found.kind === 'map' ? 'Notes on its places, as lore' : `Lorebook: ${book.name}`
  const whose = found.kind === 'map' && !(picks.main && !found.already) ? ' Without the city, they are lore for everyone in this world.' : ''
  return (
    <li>
      <Check checked={picks.book} onChange={(ticked) => change(tickBook(ticked, picks, book))} label={label} hint={`${entryCount(picks, book)}.${whose}`} />
      <div className="import-nested">
        {found.kind === 'character' && picks.book && <Owner found={found} picks={picks} change={change} />}
        <Entries book={book} picks={picks} change={change} />
      </div>
    </li>
  )
}

function Owner({ found, picks, change }: PartProps<CharacterFile>) {
  const id = useId()
  const { options, chosen } = owners(found, picks)
  return (
    <div className="field import-owner">
      <label htmlFor={id}>Whose lore</label>
      <select id={id} value={chosen} onChange={(event) => change({ loreFor: event.target.value })}>
        {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
    </div>
  )
}

function Entries({ book, picks, change }: { book: PreviewBook; picks: Picks; change: (next: Partial<Picks>) => void }) {
  const toggle = (index: number, on: boolean) => {
    const entries = new Set(picks.entries)
    if (on) entries.add(index); else entries.delete(index)
    change({ entries, book: entries.size > 0 })
  }
  return (
    <details className="import-entries">
      <summary>Choose entries</summary>
      <div className="form-actions">
        <button type="button" className="text-button" onClick={() => change({ entries: new Set(book.entries.map((_, index) => index)), book: true })}>Tick all</button>
        <button type="button" className="text-button" onClick={() => change({ entries: new Set(), book: false })}>Untick all</button>
      </div>
      <ul>
        {book.entries.map((entry, index) => <li key={index}><Check checked={picks.entries.has(index)} onChange={(on) => toggle(index, on)} label={entry.title} hint={entryHint(entry)} /></li>)}
      </ul>
    </details>
  )
}
