import { Camera } from 'lucide-react'
import type { ChatPhoto as Photo, Message } from '../../types'
import { imageFile } from '../feed/imageState'
import { photoAlt, photoLine } from './photoState'
import { usePhoto } from './usePhoto'

/** The photo a reply sent of what they were doing. Its picture is the moment's feed picture too. */
export function ChatPhoto({ message, name }: { message: Message; name: string }) {
  const photo = usePhoto(message.id, message.photo).data
  if (!photo) return null
  const line = photoLine(photo)
  return (
    <figure className={photo.kind === 'meme' ? 'chat-photo chat-meme' : 'chat-photo'}>
      <div className="chat-photo-frame">
        {photo.ref
          ? <img src={imageFile(photo.ref)} alt={photoAlt(name, photo)} loading="lazy" />
          : <span className="chat-photo-waiting" aria-hidden="true"><Camera /></span>}
        {photo.kind === 'meme' && <MemeText photo={photo} />}
      </div>
      {line && <p className={photo.status === 'failed' ? 'image-line error-text' : 'image-line subtle'} role="status">{line}</p>}
    </figure>
  )
}

/** A meme's captions in the classic top-and-bottom style, as real text so it reads and scales. */
function MemeText({ photo }: { photo: Photo }) {
  return <>
    <span className="meme-text meme-top">{photo.top_text}</span>
    <span className="meme-text meme-bottom">{photo.bottom_text}</span>
  </>
}
