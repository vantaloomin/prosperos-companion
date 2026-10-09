import { useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { FileUp } from 'lucide-react'
import { api } from '../../api'
import { COMPANION_KEY } from '../../companion'
import type { Companion } from '../../types'
import { Notice } from '../../components/Feedback'
import { fileData } from './helper'
import { IMPORT_TYPES, broughtText, type Brought } from './loreText'

/** A character card, CHARX, Backyard file or lorebook from another app, imported straight away. The world gives
 * them a job, a home and a routine; everything can be changed on this page afterwards. */
export function BringCharacter() {
  const client = useQueryClient()
  const input = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const bring = async (file: File | undefined) => {
    if (!file) return
    setBusy(true)
    setResult(null)
    try {
      const made = await api<Brought & { companion: Companion | null }>('/import/character', { filename: file.name, data: await fileData(file) })
      if (made.companion) client.setQueryData(COMPANION_KEY, made.companion)
      await Promise.all(['cast', 'lore', 'versions'].map((key) => client.invalidateQueries({ queryKey: [key] })))
      setResult({ tone: 'info', text: broughtText(made) })
    } catch (failure) {
      setResult({ tone: 'error', text: failure instanceof Error ? failure.message : 'That file could not be imported.' })
    } finally {
      setBusy(false)
      if (input.current) input.current.value = ''
    }
  }
  return (
    <section className="settings-section form-stack" aria-labelledby="bring-heading">
      <div>
        <h2 id="bring-heading">Bring your characters</h2>
        <p className="subtle">A character from SillyTavern, Chub, Agnai, RisuAI, NovelAI or Backyard moves into town with a job, a home and a routine of their own, and their lorebook comes along. A lorebook on its own becomes part of this world.</p>
      </div>
      <input ref={input} type="file" accept={IMPORT_TYPES} hidden onChange={(event) => void bring(event.target.files?.[0])} />
      <div className="form-actions">
        <button type="button" className="button" disabled={busy} onClick={() => input.current?.click()}>
          <FileUp aria-hidden="true" />{busy ? 'Importing…' : 'Import a character or lorebook'}
        </button>
      </div>
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
    </section>
  )
}
