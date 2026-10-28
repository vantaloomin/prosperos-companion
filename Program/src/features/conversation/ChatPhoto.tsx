import { useState, type CSSProperties } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { ImageOff, Play, RefreshCw, RotateCcw, Trash2, Undo2 } from 'lucide-react'
import { Lightbox } from '../../components/Lightbox'
import { api } from '../../api'
import type { ChatPhoto as Photo, Message } from '../../types'
import { imageFile } from '../feed/imageState'
import { MemeLines } from '../../components/MemeLines'
import { reducedMotion } from '../../motion'
import { canRetry, fittedSize, photoAlt, photoLine, photoShape, photoSource } from './photoState'
import { useEraWords } from '../world/useEraWords'
import type { PhotoEdit } from './usePhotoEdit'
import { shownAt } from './held'

/**
 * The photo a reply sent of what they were doing. Its picture is the moment's feed picture too.
 * Until it lands, the frame holds its final shape with a blurry picture filling in, like a photo
 * coming through on a slow connection, so nothing moves when the real one arrives.
 */
export function ChatPhoto({ message, name, edit }: { message: Message; name: string; edit: PhotoEdit }) {
  const words = useEraWords()
  const photo = edit.photo
  if (!photo) return null
  if (photo.removed) return edit.undo ? <Removed edit={edit} /> : null
  const line = edit.error || (edit.coming ? 'A new picture is on its way.' : photoLine(photo, words))
  return (
    <figure className={photo.kind === 'meme' ? 'chat-photo chat-meme' : 'chat-photo'}>
      <PhotoFrame photo={photo} name={name} when={shownAt(message)} edit={edit} />
      {line && <PhotoLine photo={photo} line={line} failed={!!edit.error} />}
      {photo.source === 'gif' && <GiphyCredit page={photo.page} />}
    </figure>
  )
}

/** Where a picture the user just removed was: a quiet line with Undo, until they leave the chat. */
function Removed({ edit }: { edit: PhotoEdit }) {
  return (
    <p className={edit.error ? 'image-line chat-photo-removed error-text' : 'image-line chat-photo-removed subtle'} role="status">
      {edit.error || 'Picture removed.'}
      <button type="button" className="text-button" disabled={edit.busy} onClick={edit.restore}><Undo2 aria-hidden="true" />Undo</button>
    </p>
  )
}

/** With a mouse, a new picture or Remove shows on the picture while it is hovered or focused; on a touch screen they
 * are in the reply's sheet (press and hold, useMessageSheet.tsx) and these stay hidden (styles.css). */
function PhotoTools({ edit, ready }: { edit: PhotoEdit; ready: boolean }) {
  if (!ready || (!edit.canReroll && !edit.canRemove)) return null
  return (
    <span className="chat-photo-tools">
      {edit.canReroll && <button type="button" className="photo-tool" title="New picture" aria-label="New picture" disabled={edit.busy} onClick={edit.reroll}><RefreshCw aria-hidden="true" /></button>}
      {edit.canRemove && <button type="button" className="photo-tool" title="Remove picture" aria-label="Remove picture" disabled={edit.busy} onClick={edit.remove}><Trash2 aria-hidden="true" /></button>}
    </span>
  )
}

/** The frame in the photo's final shape: the loading picture until the real one has loaded, then the photo. A template
 * or a GIF under a meme keeps its own shape. */
function PhotoFrame({ photo, name, when, edit }: { photo: Photo; name: string; when: string; edit: PhotoEdit }) {
  const [loaded, setLoaded] = useState<string | null>(null)
  const [playing, setPlaying] = useState(false)
  const words = useEraWords()
  const failed = canRetry(photo)
  const held = heldStill(photo, playing)
  const src = held ?? photoSource(photo, imageFile)
  const landed = !!src && loaded === src
  return (
    <div {...frameLook(photo, landed)}>
      <span className={failed ? 'chat-photo-loading failed' : 'chat-photo-loading'} aria-hidden="true">{failed && <ImageOff />}</span>
      {src && <img src={src} alt={photoAlt(name, photo, words)} onLoad={() => setLoaded(src)} onError={() => setLoaded(src)} />}
      {landed && src && <Landed photo={photo} src={src} name={name} when={when} />}
      {!!held && <button type="button" className="gif-play" aria-label="Play GIF" onClick={() => setPlaying(true)}><Play aria-hidden="true" /></button>}
      <PhotoTools edit={edit} ready={landed || failed} />
    </div>
  )
}

/** Over a landed picture: a meme's captions, and full size on click (not for a GIF, which opens on GIPHY). */
function Landed({ photo, src, name, when }: { photo: Photo; src: string; name: string; when: string }) {
  return <>
    {photo.kind === 'meme' && <MemeLines top={photo.top_text} bottom={photo.bottom_text} boxes={photo.boxes} />}
    {photo.source !== 'gif' && <OpenFullSize photo={photo} src={src} name={name} when={when} />}
  </>
}

/** The frame's class and, for a template or GIF, its own shape. */
function frameLook(photo: Photo, landed: boolean): { className: string; style?: CSSProperties } {
  const fitted = fittedSize(photo)
  return { className: `chat-photo-frame photo-${fitted ? 'fitted' : photoShape(photo)}${landed ? ' landed' : ''}`, style: (fitted as CSSProperties) ?? undefined }
}

/** With motion reduced, a GIF shows its first frame until played. */
const heldStill = (photo: Photo, playing: boolean) => photo.still && !playing && reducedMotion() ? photo.still : null

/** GIPHY's terms ask for its credit wherever its GIFs show. */
function GiphyCredit({ page }: { page?: string }) {
  return <p className="gif-credit subtle">{page ? <a href={page} target="_blank" rel="noreferrer noopener">Powered by GIPHY</a> : 'Powered by GIPHY'}</p>
}

/** Clicking a landed photo opens it at full size, a meme with its captions. */
function OpenFullSize({ photo, src, name, when }: { photo: Photo; src: string; name: string; when: string }) {
  const [open, setOpen] = useState(false)
  const words = useEraWords()
  const captions = photo.kind === 'meme' ? { top: photo.top_text, bottom: photo.bottom_text, boxes: photo.boxes } : {}
  return <>
    <button type="button" className="photo-open" aria-label="View full size" onClick={() => setOpen(true)} />
    {open && <Lightbox pictures={[{ src, alt: photoAlt(name, photo, words), from: name, when, ...captions }]} onClose={() => setOpen(false)} />}
  </>
}

/** A plain line under a photo still coming, or one that could not be made with Try again. */
function PhotoLine({ photo, line, failed: editFailed }: { photo: Photo; line: string; failed: boolean }) {
  const client = useQueryClient()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const retry = async () => {
    setBusy(true)
    setError('')
    try {
      client.setQueryData(['chat-photo', photo.message_id], await api<Photo>(`/images/photos/${encodeURIComponent(photo.message_id)}/retry`, {}))
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'That did not work. Please try again.')
    } finally { setBusy(false) }
  }
  const failed = canRetry(photo)
  return (
    <p className={failed || editFailed ? 'image-line error-text' : 'image-line subtle'} role="status">
      {error || line}
      {failed && photo.job_id && <button type="button" className="text-button" disabled={busy} onClick={() => void retry()}><RotateCcw aria-hidden="true" />Try again</button>}
    </p>
  )
}
