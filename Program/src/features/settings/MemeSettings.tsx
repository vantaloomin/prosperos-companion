import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { FolderOpen } from 'lucide-react'
import { api } from '../../api'
import { shownPath, useRefetchOnFocus } from '../../paths'
import type { ImageSettings as Limits, MemeSources } from '../../types'
import { Notice } from '../../components/Feedback'
import { InfoTip } from '../../components/InfoTip'
import { SettingRow, SwitchRow } from '../../components/Rows'
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
    <section className="row-group meme-settings" aria-labelledby="memes-heading">
      <h3 id="memes-heading" className="section-title">Memes and GIFs<InfoTip id="memes-tip" label="Memes and GIFs" text="Memes need no picture model. The app writes the captions from their day and picks a picture to go under them. With a model above, some memes are made by it too." /></h3>
      <div className="row-list">
        <SwitchRow label="Download classic meme formats" checked={data.meme_formats} onChange={(value) => void save({ meme_formats: value })} tip={formatsHint(found)} />
        {found && (found.key_here ? <GifKey hasKey={found.gif_key} /> : <GifKeyOnPc hasKey={found.gif_key} />)}
        {!phone && found && <OwnTemplates sources={found} />}
      </div>
    </section>
  )
}

function formatsHint(found?: MemeSources) {
  const here = found?.formats_on ? ` ${found.formats_here} of ${found.formats_total} here so far.` : ''
  return `Formats like the This is Fine dog, from memegen.link, kept on this computer. Only the format's name is sent. Off: the starter pack and your own pictures.${here}`
}

/** The user's own folder of pictures, opened on the PC. */
function OwnTemplates({ sources }: { sources: MemeSources }) {
  const [problem, setProblem] = useState('')
  const open = async () => {
    setProblem('')
    try { await api('/images/memes/folder/open', {}) } catch (error) { setProblem(failure(error, "Couldn't open the folder.")) }
  }
  return (
    <div className="setting-row meme-folder">
      <span className="fold-text">
        <span className="setting-row-label">Your meme templates<InfoTip id="meme-folder-tip" label="Your meme templates"
          text={`Put JPEG, PNG, WebP or GIF pictures in this folder and they're used for memes too, with the captions at the top and bottom. Memes also use a starter pack of ${sources.pack} public-domain pictures that comes with the app.`} /></span>
        <span className="row-sub meme-folder-path">{countText(sources.mine, 'picture', 'pictures', 'No pictures yet')} · {shownPath(sources.folder)}</span>
        {problem && <Notice tone="error">{problem}</Notice>}
      </span>
      <button type="button" className="text-button" onClick={() => void open()}><FolderOpen size={15} aria-hidden="true" />Open folder</button>
    </div>
  )
}

/** Over home Wi-Fi, which is not encrypted, the key is added on the PC instead (companion/images/routes.py). */
function GifKeyOnPc({ hasKey }: { hasKey: boolean }) {
  return (
    <div className="setting-row">
      <span className="setting-row-label">Reaction GIFs<InfoTip id="gif-pc-tip" label="Reaction GIFs" text="Your GIPHY key is added on your PC, in Settings > Pictures, or on this phone over Tailscale. Home Wi-Fi is not encrypted, so keys are never sent over it." /></span>
      <span className="row-value">{hasKey ? 'On' : 'Off'}</span>
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
  return <>
    <SettingRow label="GIPHY key" tip={`Add your own free GIPHY key and your companions can send reaction GIFs. Without one, they still send memes. ${GIF_TIP}`}>
      {(id) => <span className="key-row">
        <input id={id} type="password" autoComplete="off" value={draft} maxLength={200} placeholder={hasKey ? 'Saved' : 'Paste a key'} onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => { if (event.key === 'Enter' && draft.trim()) { event.preventDefault(); void store(draft.trim(), 'Saved. Reaction GIFs are on.') } }} />
        {draft.trim() && <button type="button" className="text-button" onClick={() => void store(draft.trim(), 'Saved. Reaction GIFs are on.')}>Save</button>}
        {hasKey && !draft && <button type="button" className="text-button" onClick={() => void store('', 'Key removed. Reaction GIFs are off.')}>Remove</button>}
      </span>}
    </SettingRow>
    {result && <div className="setting-row row-note"><Notice tone={result.tone}>{result.text}</Notice></div>}
  </>
}
