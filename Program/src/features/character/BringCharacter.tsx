import { useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { FileUp } from 'lucide-react'
import { api, upload } from '../../api'
import { COMPANION_KEY } from '../../companion'
import type { Companion } from '../../types'
import { Notice } from '../../components/Feedback'
import { fileData } from './helper'
import { IMPORT_TYPES, MAX_BYTES, broughtText, carriedText, isSavedCompanion, slimmed, type Brought, type BroughtBook, type Carried } from './loreText'
import { ImportPicks } from './ImportPicks'
import { pickBody, type CharacterFile, type FileContents, type MapFile, type Picks } from './importPicksText'
import { isWorldMap, readWorldMap } from '../world/worldMap'
import { refocus } from './refocus'

type Result = { tone: 'info' | 'error'; text: string }
/** A file read and listed, waiting for Import: what is sent again with the picks. */
type Opened = { filename: string; found: FileContents; body: { filename: string; data: string } | { map: unknown } }
/** The last import's outcome, kept outside the section: the new companion remounts the whole Character page, which
 * would otherwise lose the "is here" notice the moment it is set. */
let latest: (Result & { at: number }) | null = null
const KEEP_MS = 30_000

/** Read a file and list what it holds; nothing is saved. A world map is read without its pictures. */
async function open(file: File): Promise<Opened> {
  if (isWorldMap(file.name, await file.slice(0, 4096).text())) {
    const map = await readWorldMap(file)
    const found = await api<Omit<MapFile, 'kind'>>('/world/import/marinara/inspect', map)
    return { filename: file.name, found: { ...found, kind: 'map' }, body: { map } }
  }
  const sent = await slimmed(file)
  if (sent.size > MAX_BYTES) throw new Error('Character files are limited to 10 MB.')
  const body = { filename: file.name, data: await fileData(sent) }
  const found = await api<Omit<CharacterFile, 'kind'>>('/import/character/inspect', body)
  return { filename: file.name, found: { ...found, kind: 'character' }, body }
}

function mapText(city: { name: string | null; book: BroughtBook | null }): string {
  const lore = city.book ? `${city.book.entries} of its places' notes are world lore in "${city.book.name}".` : ''
  if (!city.name) return lore || 'Nothing was imported.'
  return `${city.name} is now one of your cities, in Settings > Life & cities.${lore ? ` ${lore}` : ''}`
}

/** A character card, CHARX, Backyard file, lorebook or world map from another app. The page lists what the file
 * holds, all of it ticked, and imports what stays ticked. The world gives a character a job, a home and a routine;
 * everything can be changed on this page afterwards. */
export function BringCharacter() {
  const client = useQueryClient()
  const input = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [opened, setOpened] = useState<Opened | null>(null)
  const [result, showResult] = useState<Result | null>(() => latest && Date.now() - latest.at < KEEP_MS ? latest : null)
  const setResult = (next: Result | null) => {
    latest = next && { ...next, at: Date.now() }
    showResult(next)
  }
  const run = async (work: () => Promise<void>, fallback: string) => {
    setBusy(true)
    setResult(null)
    try { await work() } catch (failure) {
      setResult({ tone: 'error', text: failure instanceof Error ? failure.message : fallback })
    } finally {
      setBusy(false)
      if (input.current) input.current.value = ''
    }
  }
  const choose = (file: File | undefined) => {
    if (!file) return
    setOpened(null)
    if (isSavedCompanion(file.name)) { carry(file); return }
    void run(async () => setOpened(await open(file)), 'That file could not be read.')
  }
  // A companion saved in another world arrives straight away with their history (companion/carry.py): nothing to pick.
  const carry = (file: File) => void run(async () => {
    const made = await upload<Carried & { companion: Companion | null }>('/export/companion', file, { name: file.name })
    setResult({ tone: 'info', text: carriedText(made) })  // Before the page remounts for them.
    await refocus(client)
  }, 'That companion could not be opened here.')
  const bring = (picks: Picks) => void run(async () => {
    if (!opened) return
    const pick = pickBody(opened.found, picks)
    if (opened.found.kind === 'map') {
      const city = await api<{ name: string | null; book: BroughtBook | null }>('/world/import/marinara/picked', { ...opened.body, pick })
      setOpened(null)
      setResult({ tone: 'info', text: mapText(city) })
      await Promise.all(['cities', 'lore'].map((key) => client.invalidateQueries({ queryKey: [key] })))
      return
    }
    const made = await api<Brought & { companion: Companion | null }>('/import/character', { ...opened.body, pick })
    setOpened(null)
    setResult({ tone: 'info', text: broughtText(made) })  // Before the page remounts for the new companion.
    if (made.companion) client.setQueryData(COMPANION_KEY, made.companion)
    await Promise.all(['cast', 'lore', 'versions'].map((key) => client.invalidateQueries({ queryKey: [key] })))
  }, 'That file could not be imported.')
  return (
    <section className="settings-section form-stack" aria-labelledby="bring-heading">
      <div>
        <h2 id="bring-heading">Bring your characters</h2>
        <p className="subtle">A character from SillyTavern, Chub, Agnai, RisuAI, NovelAI, Backyard or Marinara Engine moves into town with a job, a home and a routine of their own, and their lorebook comes along. A lorebook on its own becomes part of this world. You see what a file holds before anything is imported. A companion saved from another world arrives straight away, with all their history.</p>
      </div>
      <input ref={input} type="file" accept={IMPORT_TYPES} hidden onChange={(event) => choose(event.target.files?.[0])} />
      {!opened && <div className="form-actions">
        <button type="button" className="button" disabled={busy} onClick={() => input.current?.click()}>
          <FileUp aria-hidden="true" />{busy ? 'Reading…' : 'Import a character or lorebook'}
        </button>
      </div>}
      {opened && <ImportPicks key={opened.filename} filename={opened.filename} found={opened.found} busy={busy} onImport={bring} onCancel={() => setOpened(null)} />}
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
    </section>
  )
}
