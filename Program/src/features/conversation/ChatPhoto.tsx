import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { ImageOff, RotateCcw } from 'lucide-react'
import { Lightbox } from '../../components/Lightbox'
import { api } from '../../api'
import type { ChatPhoto as Photo, Message } from '../../types'
import { imageFile } from '../feed/imageState'
import { MemeLines } from '../../components/MemeLines'
import { canRetry, fittedSize, photoAlt, photoLine, photoShape, photoSource } from './photoState'
import { usePhoto } from './usePhoto'

/**
 * The photo a reply sent of what they were doing. Its picture is the moment's feed picture too.
 * Until it lands, the frame holds its final shape with a blurry picture filling in, like a photo
 * coming through on a slow connection, so nothing moves when the real one arrives.
 */
export function ChatPhoto({ message, name }: { message: Message; name: string }) {
  const photo = usePhoto(message.id, message.photo).data
  if (!photo) return null
  const line = photoLine(photo)
  return (
    <figure className={photo.kind === 'meme' ? 'chat-photo chat-meme' : 'chat-photo'}>
      <PhotoFrame photo={photo} name={name} when={message.created_at} />
      {line && <PhotoLine photo={photo} line={line} />}
      {photo.source === 'gif' && <GiphyCredit page={photo.page} />}
    </figure>
  )
}

/** The frame in the photo's final shape: the loading picture until the real one has loaded, then the photo. A template
 * or a GIF under a meme keeps its own shape. */
function PhotoFrame({ photo, name, when }: { photo: Photo; name: string; when: string }) {
  const [loaded, setLoaded] = useState<string | null>(null)
  const failed = canRetry(photo)
  const src = photoSource(photo, imageFile)
  const landed = !!src && loaded === src
  const fitted = fittedSize(photo)
  return (
    <div className={`chat-photo-frame photo-${fitted ? 'fitted' : photoShape(photo)}${landed ? ' landed' : ''}`} style={fitted ?? undefined}>
      <span className={failed ? 'chat-photo-loading failed' : 'chat-photo-loading'} aria-hidden="true">{failed && <ImageOff />}</span>
      {src && <img src={src} alt={photoAlt(name, photo)} onLoad={() => setLoaded(src)} onError={() => setLoaded(src)} />}
      {landed && src && <Landed photo={photo} src={src} name={name} when={when} />}
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

/** GIPHY's terms ask for its credit wherever its GIFs show. */
function GiphyCredit({ page }: { page?: string }) {
  return <p className="gif-credit subtle">{page ? <a href={page} target="_blank" rel="noreferrer noopener">Powered by GIPHY</a> : 'Powered by GIPHY'}</p>
}

/** Clicking a landed photo opens it at full size, a meme with its captions. */
function OpenFullSize({ photo, src, name, when }: { photo: Photo; src: string; name: string; when: string }) {
  const [open, setOpen] = useState(false)
  const captions = photo.kind === 'meme' ? { top: photo.top_text, bottom: photo.bottom_text, boxes: photo.boxes } : {}
  return <>
    <button type="button" className="photo-open" aria-label="View full size" onClick={() => setOpen(true)} />
    {open && <Lightbox pictures={[{ src, alt: photoAlt(name, photo), from: name, when, ...captions }]} onClose={() => setOpen(false)} />}
  </>
}

/** A plain line under a photo still coming, or one that could not be made with Try again. */
function PhotoLine({ photo, line }: { photo: Photo; line: string }) {
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
    <p className={failed ? 'image-line error-text' : 'image-line subtle'} role="status">
      {error || line}
      {failed && photo.job_id && <button type="button" className="text-button" disabled={busy} onClick={() => void retry()}><RotateCcw aria-hidden="true" />Try again</button>}
    </p>
  )
}
