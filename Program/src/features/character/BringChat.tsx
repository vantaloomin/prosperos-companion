import { useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { FileUp } from 'lucide-react'
import { api } from '../../api'
import { HISTORY_KEY, MEMORIES_KEY } from '../../companion'
import type { Companion } from '../../types'
import { Notice } from '../../components/Feedback'
import { fileData } from './helper'
import { CHAT_FILE_LIMIT, importedText, type ChatImportResult } from './chatImportText'

type Result = { tone: 'info' | 'error'; text: string }

/** An old chat with this companion (a SillyTavern .jsonl or a JSON list of messages), brought in straight away as the
 * history before their chat here. No review and no questions; the page only says what came in. */
export function BringChat({ companion }: { companion: Companion }) {
  const client = useQueryClient()
  const input = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<Result | null>(null)
  const name = companion.version.name
  const bring = async (file: File | undefined) => {
    if (!file) return
    setResult(null)
    if (file.size === 0 || file.size > CHAT_FILE_LIMIT) {
      setResult({ tone: 'error', text: file.size ? 'Chat files are limited to 10 MB.' : 'That file is empty.' })
      if (input.current) input.current.value = ''
      return
    }
    setBusy(true)
    try {
      const made = await api<ChatImportResult>('/import/chat', { filename: file.name, data: await fileData(file), companion_id: companion.id })
      setResult({ tone: 'info', text: importedText(made) })
      await Promise.all([HISTORY_KEY, MEMORIES_KEY, ['chats']].map((queryKey) => client.invalidateQueries({ queryKey })))
    } catch (failure) {
      setResult({ tone: 'error', text: failure instanceof Error ? failure.message : 'That chat could not be brought in.' })
    } finally {
      setBusy(false)
      if (input.current) input.current.value = ''
    }
  }
  return (
    <section className="settings-section form-stack" aria-labelledby="bring-chat-heading">
      <div>
        <h2 id="bring-chat-heading">Bring an old chat</h2>
        <p className="subtle">A SillyTavern chat (.jsonl) or a JSON list of messages with {name} becomes the history before your chat here. Its dates are kept when the file has them, and what you said in it is remembered the usual way.</p>
      </div>
      <input ref={input} type="file" accept=".jsonl,.json,application/json" hidden onChange={(event) => void bring(event.target.files?.[0])} />
      <div className="form-actions">
        <button type="button" className="button" disabled={busy} onClick={() => input.current?.click()}>
          <FileUp aria-hidden="true" />{busy ? 'Bringing it in…' : 'Import a chat'}
        </button>
      </div>
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
    </section>
  )
}
