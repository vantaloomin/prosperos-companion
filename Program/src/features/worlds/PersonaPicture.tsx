import { useEffect, useRef, useState, type ChangeEvent } from 'react'
import { ImagePlus, Sparkles } from 'lucide-react'
import { api, upload } from '../../api'
import type { Persona, Worlds } from '../../types'
import { Notice } from '../../components/Feedback'
import { profileCopy } from '../appearance/browserImage'

interface Making { status: 'queued' | 'running' | 'completed' | 'failed' | null; error: string | null; can_make: boolean }
type Busy = 'adding' | 'making' | 'removing' | null

const failure = (error: unknown, fallback: string) => error instanceof Error ? error.message : fallback
// How long Make one waits before saying it is taking a while; the picture still lands when it is done.
const WAIT_MS = 3 * 60 * 1000
const SLOW = 'This is taking a while. It will appear here when it\'s done.'

/** The persona's picture (companion/persona_pictures.py): one the user picks, or one made from How you look. Pictures
 * of moments they share with a companion follow it. `looks` is How you look as typed; Make one saves it first. */
export function PersonaPicture({ persona, looks, onChange }: { persona: Persona; looks: string; onChange: (data: Worlds) => void }) {
  const input = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState<Busy>(null)
  const [error, setError] = useState<string | null>(null)
  const [canMake, setCanMake] = useState(true)
  const base = `/worlds/personas/${persona.id}/picture`
  useEffect(() => { api<Making>(`${base}/make`).then((state) => setCanMake(state.can_make)).catch(() => undefined) }, [base])
  const act = async (kind: NonNullable<Busy>, action: () => Promise<Worlds | undefined>, fallback: string) => {
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
    await api<Making>(`${base}/make`, { looks })
    const done = await waitFor(`${base}/make`)
    if (done === null) throw new Error(SLOW)
    if (done.status === 'failed') throw new Error(done.error ?? 'Your picture could not be made.')
    return api<Worlds>('/worlds')
  }, 'Your picture could not be made.')
  const remove = () => act('removing', () => api<Worlds>(base, undefined, 'DELETE'), 'The picture was not removed.')
  const making = busy === 'making'
  return (
    <fieldset className="persona-picture">
      <legend>Your picture</legend>
      <div className="own-picture">
        <div className={`persona-picture-frame${making ? ' making' : ''}`} aria-busy={making}>
          {persona.picture
            ? <img src={`/api${base}?v=${encodeURIComponent(persona.picture)}`} alt="Your picture" />
            : <div className="persona-picture-empty" aria-hidden="true"><ImagePlus /></div>}
        </div>
        <div className="form-stack">
          <p className="subtle" id="persona-picture-hint">
            Pictures of you with a companion, like a dinner out or an evening at home, follow this picture. It is only sent to the image backend making that picture.
          </p>
          <input ref={input} type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={(event) => void choose(event)} />
          <PictureActions busy={busy} picture={!!persona.picture} looks={!!looks.trim()} canMake={canMake} onPick={() => input.current?.click()} onMake={() => void make()} onRemove={() => void remove()} />
          <span className="visually-hidden" role="status">{making ? 'Making your picture.' : ''}</span>
          <div aria-live="polite">{error && <Notice tone={error === SLOW ? 'info' : 'error'}>{error}</Notice>}</div>
        </div>
      </div>
    </fieldset>
  )
}

/** Until the picture is made or has failed, checking every two seconds; null once it has taken longer than WAIT_MS. */
async function waitFor(path: string): Promise<Making | null> {
  const until = Date.now() + WAIT_MS
  while (Date.now() < until) {
    const state = await api<Making>(path)
    if (state.status !== 'queued' && state.status !== 'running') return state
    await new Promise((resolve) => setTimeout(resolve, 2000))
  }
  return null
}

interface ActionsProps { busy: Busy; picture: boolean; looks: boolean; canMake: boolean; onPick: () => void; onMake: () => void; onRemove: () => void }

function makeHint(picture: boolean, looks: boolean, canMake: boolean): string {
  if (!canMake) return 'To make one, add an image backend in Settings > Images.'
  if (!looks) return 'Say how you look above to make one.'
  return picture ? 'Make a new one draws you from How you look and replaces this picture.' : 'Make one draws you from How you look, with this world\'s image backends.'
}

function PictureActions({ busy, picture, looks, canMake, onPick, onMake, onRemove }: ActionsProps) {
  return <>
    <div className="persona-picture-actions">
      <button type="button" className="button" disabled={busy !== null} aria-describedby="persona-picture-hint" onClick={onPick}>
        <ImagePlus aria-hidden="true" />{busy === 'adding' ? 'Adding the picture…' : picture ? 'Choose another picture' : 'Choose a picture'}
      </button>
      <button type="button" className="button" disabled={busy !== null || !looks || !canMake} aria-describedby="persona-make-hint" onClick={onMake}>
        <Sparkles aria-hidden="true" />{busy === 'making' ? 'Making your picture…' : picture ? 'Make a new one' : 'Make one'}
      </button>
      {picture && <button type="button" className="text-button" disabled={busy !== null} onClick={onRemove}>{busy === 'removing' ? 'Removing…' : 'Remove'}</button>}
    </div>
    <p className="subtle" id="persona-make-hint">{makeHint(picture, looks, canMake)}</p>
  </>
}
