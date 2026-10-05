import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { Notice } from '../../components/Feedback'
import { TextArea } from '../../components/Fields'

export interface DraftingPrompt { name: string; label: string; description: string; text: string; default: string; customized: boolean; placeholders: string[] }

const KEY = ['prompts']

/** The instructions sent to the text model when it helps create a character (docs/character-drafting.md). */
export function PromptSettings() {
  const prompts = useQuery({ queryKey: KEY, queryFn: () => api<DraftingPrompt[]>('/prompts') })
  if (!prompts.data) return null
  return (
    <section className="settings-section form-stack" aria-labelledby="prompts-heading">
      <div>
        <h2 id="prompts-heading">Character drafting prompts</h2>
        <p className="subtle">What your text model is told when it drafts a character or rewrites a field. Changes apply to the next draft. Words in double braces, such as {'{{rules}}'}, are filled in by the app and must stay.</p>
      </div>
      {prompts.data.map((prompt) => <PromptEditor key={prompt.name} prompt={prompt} />)}
    </section>
  )
}

function PromptEditor({ prompt }: { prompt: DraftingPrompt }) {
  const client = useQueryClient()
  const [text, setText] = useState(prompt.text)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const run = async (request: () => Promise<DraftingPrompt>, done: string) => {
    setBusy(true)
    try {
      const saved = await request()
      setText(saved.text)
      client.setQueryData<DraftingPrompt[]>(KEY, (current) => current?.map((item) => item.name === saved.name ? saved : item))
      setResult({ tone: 'info', text: done })
    } catch (error) {
      setResult({ tone: 'error', text: error instanceof Error ? error.message : 'Not saved.' })
    } finally { setBusy(false) }
  }
  const save = () => run(() => api<DraftingPrompt>(`/prompts/${prompt.name}`, { text }, 'PUT'), 'Saved. The next draft uses it.')
  const reset = () => run(() => api<DraftingPrompt>(`/prompts/${prompt.name}`, undefined, 'DELETE'), 'Back to the original wording.')
  const placeholders = prompt.placeholders.map((key) => `{{${key}}}`).join(', ')
  return (
    <details className="prompt-editor">
      <summary>{prompt.label}{prompt.customized && <span className="badge">Your wording</span>}</summary>
      <TextArea label={prompt.description} value={text} onChange={setText} rows={16} maxLength={20000}
        hint={placeholders ? `Must keep: ${placeholders}.` : undefined} />
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
      <div className="form-actions">
        <button type="button" className="button primary" disabled={busy || !text.trim() || text === prompt.text} onClick={() => void save()}>Save</button>
        {prompt.customized && <button type="button" className="button" disabled={busy} onClick={() => void reset()}>Reset to original</button>}
        {text !== prompt.text && <button type="button" className="text-button" disabled={busy} onClick={() => setText(prompt.text)}>Discard changes</button>}
      </div>
    </details>
  )
}
