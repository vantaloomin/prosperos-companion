import { useState, type FormEvent } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api, ApiError } from '../../api'
import { COMPANION_KEY } from '../../companion'
import { Notice } from '../../components/Feedback'
import { Field, TextInput } from '../../components/Fields'
import { fieldLine, splitFields, studyVersionLabel, type StudyCharacterSummary, type StudyImportResult, type StudyReview, type StudyWorkspace } from './studyReview'

/** Optional reviewed import of one character from a Prospero's Study workspace. Nothing is copied until Import. */
export function StudyImport() {
  const client = useQueryClient()
  const [path, setPath] = useState('')
  const [found, setFound] = useState<{ workspace: StudyWorkspace; characters: StudyCharacterSummary[] } | null>(null)
  const [characterId, setCharacterId] = useState('')
  const [review, setReview] = useState<StudyReview | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<{ text: string; stale?: boolean } | null>(null)

  const run = async (work: () => Promise<void>) => {
    setBusy(true); setError(null)
    try { await work() } catch (failure) {
      setError({ text: failure instanceof Error ? failure.message : 'The Study workspace could not be read.', stale: failure instanceof ApiError && failure.status === 409 && review !== null })
    } finally { setBusy(false) }
  }
  const inspect = (event: FormEvent) => {
    event.preventDefault()
    void run(async () => {
      setReview(null)
      const data = await api<{ workspace: StudyWorkspace; characters: StudyCharacterSummary[] }>('/import/study/inspect', { path: path.trim() })
      setFound(data); setCharacterId(data.characters[0]?.id ?? '')
    })
  }
  const prepare = (id = characterId) => run(async () => { setReview(await api<StudyReview>('/import/study/review', { path: path.trim(), character_id: id })) })
  const confirm = () => run(async () => {
    if (!review) return
    const result = await api<StudyImportResult>('/import/study', { path: path.trim(), character_id: review.source.character_id, review_token: review.review_token })
    client.setQueryData(COMPANION_KEY, result.companion)
  })

  return (
    <details className="study-import">
      <summary>Import from Prospero&rsquo;s Study</summary>
      <div className="form-stack">
        <p className="subtle">Copy one character&rsquo;s definition and artwork from a Study workspace. The Study is only read, never changed, and you see everything that would be copied before anything is.</p>
        <form className="study-import-row" onSubmit={inspect}>
          <TextInput label="Study folder or database file" value={path} onChange={(value) => { setPath(value); setFound(null); setReview(null) }} placeholder="C:\Users\you\prosperos-study" hint="The folder holding data/roleplay.sqlite3, or the file itself." />
          <button type="submit" className="button" disabled={busy || !path.trim()}>Look inside</button>
        </form>
        {found && (found.characters.length === 0
          ? <Notice>This Study workspace has no characters in its library.</Notice>
          : <div className="study-import-row">
              <Field label="Character" hint="Characters found in that Study workspace. Nothing is copied until you review it.">
                {(id, hint) => <select id={id} aria-describedby={hint} value={characterId} onChange={(event) => { setCharacterId(event.target.value); setReview(null) }}>
                  {found.characters.map((item) => <option key={item.id} value={item.id}>{item.name} (version {item.version_number}{item.has_artwork ? ', with artwork' : ''})</option>)}
                </select>}
              </Field>
              <button type="button" className="button" disabled={busy || !characterId} onClick={() => void prepare()}>Review</button>
            </div>)}
        {error && <Notice tone="error" action={error.stale && review ? <button type="button" className="text-button" onClick={() => void prepare(review.source.character_id)}>Review again</button> : undefined}>{error.text}</Notice>}
        {review && <ReviewPanel review={review} busy={busy} onImport={() => void confirm()} />}
      </div>
    </details>
  )
}

function ReviewPanel({ review, busy, onImport }: { review: StudyReview; busy: boolean; onImport: () => void }) {
  const { included, left } = splitFields(review.fields)
  return (
    <section className="study-review" aria-label="Import review">
      <h2>{review.source.name}, version {review.source.version_number}</h2>
      <h3>Copied into the new companion</h3>
      <ul className="plain-list">{included.map((field) => <li key={field.source}>{fieldLine(field)}</li>)}</ul>
      {left.length > 0 && <><h3>In this character, but not copied</h3><ul className="plain-list">{left.map((field) => <li key={field.source}>{fieldLine(field)}</li>)}</ul></>}
      <h3>Artwork</h3>
      {review.artwork.length === 0 ? <p className="subtle">This version has no artwork.</p> : (
        <ul className="study-artwork">{review.artwork.map((item) => (
          <li key={item.sha256}>
            {item.thumbnail && <img src={item.thumbnail} alt={`Artwork for ${review.source.name}`} />}
            <span><strong>{item.status === 'included' ? 'Included' : 'Not included'}</strong>{item.width ? ` · ${item.width}×${item.height} ${item.format?.toUpperCase()}` : ''}<br /><small className="subtle">{item.reason}</small></span>
          </li>))}
        </ul>)}
      <h3>Never copied</h3>
      <ul className="plain-list">{review.exclusions.map((item) => <li key={item.item}><strong>{item.item}.</strong> {item.detail}</li>)}</ul>
      <h3>After import</h3>
      <ul className="plain-list">{review.defaults.map((line) => <li key={line}>{line}</li>)}</ul>
      <p className="subtle">Source: {review.workspace.database} · {studyVersionLabel(review.workspace)} · character {review.source.character_id}, version {review.source.version_id}. This is kept with the companion.</p>
      {review.companion_exists && <Notice tone="error">This workspace already has a companion, so nothing can be imported into it.</Notice>}
      <div className="form-actions">
        <button type="button" className="button primary" disabled={busy || review.companion_exists} onClick={onImport}>Import {review.source.name}</button>
      </div>
    </section>
  )
}
