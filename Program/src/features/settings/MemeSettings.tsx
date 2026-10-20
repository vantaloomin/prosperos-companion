import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { FolderOpen } from 'lucide-react'
import { api } from '../../api'
import { shownPath, useRefetchOnFocus } from '../../paths'
import type { ImageSettings as Limits, MemeSources } from '../../types'
import { Notice } from '../../components/Feedback'
import { TextInput, Toggle } from '../../components/Fields'
import { countText } from '../../components/numberBounds'

const MEMES_KEY = ['image-memes']
const failure = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback

const GIF_TIP = "1. Sign up at developers.giphy.com. 2. Choose Create an API Key, pick API (not SDK), and give it any name, like 'My Companion'. 3. Copy the key and paste it here. Free keys allow 100 searches an hour, plenty for chat. Only a short word like 'coffee' or 'rain' is sent to GIPHY, never your messages. GIFs are limited to the G and PG ratings."

/** Memes without an image model (companion/images/meme_pictures.py, gifs.py): where their pictures come from, and reaction GIFs with the user's own key. */
export function MemeSettings({ data, save, phone }: { data: Limits; save: (change: Partial<Limits>, done?: string) => Promise<boolean>; phone: boolean }) {
  const sources = useQuery({ queryKey: MEMES_KEY, queryFn: () => api<MemeSources>('/images/memes') })
  useRefetchOnFocus(() => void sources.refetch(), !phone)
  const found = sources.data
  return (
    <div className="form-stack meme-settings">
      <div>
        <h3 id="memes-heading">Memes and GIFs</h3>
        <p className="subtle">Memes need no image backend. The app writes the captions from their day and picks a picture to go under them. With a backend above, some memes are made by it too.</p>
      </div>
      <Toggle label="Download classic meme formats" checked={data.meme_formats} onChange={(value) => void save({ meme_formats: value })}
        hint={formatsHint(found)} />
      {!phone && found && <OwnTemplates sources={found} />}
      {found && <GifKey hasKey={found.gif_key} />}
    </div>
  )
}

function formatsHint(found?: MemeSources) {
  const here = found && found.formats_on ? ` ${found.formats_here} of ${found.formats_total} are on this computer.` : ''
  return `Formats like the This is Fine dog, downloaded from memegen.link the first time they send a meme and kept on this computer. Only the format's name is sent. Off: memes use the starter pack and your own pictures.${here}`
}

/** The user's own folder of pictures, opened on the PC. */
function OwnTemplates({ sources }: { sources: MemeSources }) {
  const [problem, setProblem] = useState('')
  const open = async () => {
    setProblem('')
    try { await api('/images/memes/folder/open', {}) } catch (error) { setProblem(failure(error, "Couldn't open the folder.")) }
  }
  return (
    <div className="meme-folder">
      <p className="meme-folder-line"><strong>Your meme templates</strong> <span className="subtle">{countText(sources.mine, 'picture', 'pictures', 'No pictures yet')}</span></p>
      <p className="subtle">Put JPEG, PNG, WebP or GIF pictures in this folder and they're used for memes too, with the captions at the top and bottom. Memes also use a starter pack of {sources.pack} public-domain pictures that comes with the app.</p>
      <div className="form-actions">
        <button type="button" className="button" onClick={() => void open()}><FolderOpen size={15} aria-hidden="true" />Open folder</button>
        <small className="subtle">{shownPath(sources.folder)}</small>
      </div>
      {problem && <Notice tone="error">{problem}</Notice>}
    </div>
  )
}

/** The user's own GIPHY key: saved in the system's credential store, never shown again. */
function GifKey({ hasKey }: { hasKey: boolean }) {
  const client = useQueryClient()
  const [draft, setDraft] = useState('')
  const [result, setResult] = useState<{ tone: 'info' | 'error'; text: string } | null>(null)
  const store = async (key: string, done: string) => {
    try {
      client.setQueryData(MEMES_KEY, await api<MemeSources>('/images/memes/gif-key', { key }, 'PUT'))
      setDraft('')
      setResult({ tone: 'info', text: done })
    } catch (error) { setResult({ tone: 'error', text: failure(error, 'Not saved.') }) }
  }
  return (
    <div className="form-stack">
      <TextInput label="GIPHY key" type="password" value={draft} onChange={setDraft} maxLength={200}
        placeholder={hasKey ? 'Saved; type a new one to replace it' : ''} tip={GIF_TIP}
        hint="Add your own free GIPHY key and your companions can send reaction GIFs. Without one, they still send memes." />
      <div className="form-actions">
        {draft.trim() && <button type="button" className="button primary" onClick={() => void store(draft.trim(), 'Saved. Reaction GIFs are on.')}>Save key</button>}
        {hasKey && !draft && <button type="button" className="button" onClick={() => void store('', 'Key removed. Reaction GIFs are off.')}>Remove key</button>}
      </div>
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
    </div>
  )
}
