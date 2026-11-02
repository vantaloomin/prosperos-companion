import { useRef, useState, type ChangeEvent } from 'react'
import { ImagePlus, Sparkles } from 'lucide-react'
import { api, upload } from '../../api'
import type { Persona, Worlds } from '../../types'
import { Notice } from '../../components/Feedback'
import { profileCopy } from '../appearance/browserImage'

interface Making { status: 'queued' | 'running' | 'completed' | 'failed' | null; error: string | null }

const failure = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback

/** The persona's picture (companion/persona_pictures.py): one the user picks, or one made from How you look. Pictures
 * of moments they share with a companion follow it. `looks` is How you look as saved. */
export function PersonaPicture({ persona, onChange }: { persona: Persona; onChange: (data: Worlds) => void }) {
  const input = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState<'adding' | 'making' | 'removing' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const base = `/worlds/personas/${persona.id}/picture`
  const act = async (kind: NonNullable<typeof busy>, action: () => Promise<Worlds | undefined>, fallback: string) => {
    setBusy(kind)
    try {
      const data = await action()
      if (data) onChange(data)
      setError(null)
    } catch (failed) { setError(failure(failed, fallback)) } finally { setBusy(null) }
  }
  const choose = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (file) await act('adding', async () => upload<Worlds>(base, await profileCopy(file), {}), 'This picture could not be used.')
  }
  const make = () => act('making', async () => {
    await api<Making>(`${base}/make`, {})
    const done = await waitFor(`${base}/make`)
    if (done.status === 'failed') throw new Error(done.error ?? 'Your picture could not be made.')
    return api<Worlds>('/worlds')
  }, 'Your picture could not be made.')
  const remove = () => act('removing', () => api<Worlds>(base, undefined, 'DELETE'), 'The picture was not removed.')
  const looks = !!persona.looks?.trim()
  return (
    <fieldset className="persona-picture">
      <legend>Your picture</legend>
      <div className="own-picture">
        {persona.picture
          ? <img src={`/api${base}?v=${encodeURIComponent(persona.picture)}`} alt="Your picture" />
          : <div className="persona-picture-empty" aria-hidden="true"><ImagePlus /></div>}
        <div className="form-stack">
          <p className="subtle" id="persona-picture-hint">
            Pictures of you with a companion, like a dinner out or an evening at home, follow this picture. It is only sent to the image backend making that picture.
          </p>
          <input ref={input} type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={(event) => void choose(event)} />
          <PictureActions busy={busy} picture={!!persona.picture} looks={looks} onPick={() => input.current?.click()} onMake={() => void make()} onRemove={() => void remove()} />
          <div aria-live="polite">{error && <Notice tone="error">{error}</Notice>}</div>
        </div>
      </div>
    </fieldset>
  )
}

/** Until the picture is made or has failed, checking every two seconds. */
async function waitFor(path: string): Promise<Making> {
  for (;;) {
    const state = await api<Making>(path)
    if (state.status !== 'queued' && state.status !== 'running') return state
    await new Promise((resolve) => setTimeout(resolve, 2000))
  }
}


interface ActionsProps { busy: 'adding' | 'making' | 'removing' | null; picture: boolean; looks: boolean; onPick: () => void; onMake: () => void; onRemove: () => void }

function PictureActions({ busy, picture, looks, onPick, onMake, onRemove }: ActionsProps) {
  return <>
    <div className="persona-picture-actions">
      <button type="button" className="button" disabled={busy !== null} aria-describedby="persona-picture-hint" onClick={onPick}>
        <ImagePlus aria-hidden="true" />{busy === 'adding' ? 'Adding…' : picture ? 'Choose another' : 'Upload a picture'}
      </button>
      <button type="button" className="button" disabled={busy !== null || !looks} aria-describedby="persona-make-hint" onClick={onMake}>
        <Sparkles aria-hidden="true" />{busy === 'making' ? 'Making your picture…' : 'Make one'}
      </button>
      {picture && <button type="button" className="text-button" disabled={busy !== null} onClick={onRemove}>{busy === 'removing' ? 'Removing…' : 'Remove'}</button>}
    </div>
    <p className="subtle" id="persona-make-hint">{looks ? 'Make one draws you from How you look, with this world\'s image backends.' : 'To make one, say how you look above and save.'}</p>
  </>
}
