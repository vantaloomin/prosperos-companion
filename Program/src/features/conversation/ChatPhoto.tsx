import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { ImageOff, RotateCcw } from 'lucide-react'
import { api } from '../../api'
import type { ChatPhoto as Photo, Message } from '../../types'
import { imageFile } from '../feed/imageState'
import { canRetry, photoAlt, photoLine, photoShape } from './photoState'
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
      <PhotoFrame photo={photo} name={name} />
      {line && <PhotoLine photo={photo} line={line} />}
    </figure>
  )
}

/** The frame in the photo's final shape: the loading picture until the real one has loaded, then the photo. */
function PhotoFrame({ photo, name }: { photo: Photo; name: string }) {
  const [loaded, setLoaded] = useState<string | null>(null)
  const failed = canRetry(photo)
  const landed = !!photo.ref && loaded === photo.ref
  return (
    <div className={`chat-photo-frame photo-${photoShape(photo)}${landed ? ' landed' : ''}`}>
      <span className={failed ? 'chat-photo-loading failed' : 'chat-photo-loading'} aria-hidden="true">{failed && <ImageOff />}</span>
      {photo.ref && <img src={imageFile(photo.ref)} alt={photoAlt(name, photo)} onLoad={() => setLoaded(photo.ref)} onError={() => setLoaded(photo.ref)} />}
      {photo.kind === 'meme' && landed && <MemeText photo={photo} />}
    </div>
  )
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

/** A meme's captions in the classic top-and-bottom style, as real text so it reads and scales. */
function MemeText({ photo }: { photo: Photo }) {
  return <>
    <span className="meme-text meme-top">{photo.top_text}</span>
    <span className="meme-text meme-bottom">{photo.bottom_text}</span>
  </>
}
