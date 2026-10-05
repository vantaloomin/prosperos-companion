import { Camera } from 'lucide-react'
import type { Message } from '../../types'
import { imageFile } from '../feed/imageState'
import { photoAlt, photoLine } from './photoState'
import { usePhoto } from './usePhoto'

/** The photo a reply sent of what they were doing. Its picture is the moment's feed picture too. */
export function ChatPhoto({ message, name }: { message: Message; name: string }) {
  const photo = usePhoto(message.id, message.photo).data
  if (!photo) return null
  const line = photoLine(photo)
  return (
    <figure className="chat-photo">
      {photo.ref
        ? <img src={imageFile(photo.ref)} alt={photoAlt(name, photo)} loading="lazy" />
        : <span className="chat-photo-waiting" aria-hidden="true"><Camera /></span>}
      {line && <p className={photo.status === 'failed' ? 'image-line error-text' : 'image-line subtle'} role="status">{line}</p>}
    </figure>
  )
}
