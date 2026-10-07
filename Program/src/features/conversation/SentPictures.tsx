import type { Message } from '../../types'
import { pictureNote } from './pictureState'

/** The pictures you sent with a message, and a note when the companion could not see one. */
export function SentPictures({ message, name }: { message: Message; name: string }) {
  const pictures = message.pictures ?? []
  if (!pictures.length) return null
  return (
    <div className="sent-pictures">
      {pictures.map((picture, index) => {
        const note = pictureNote(picture, name)
        return <figure key={picture.id} className="sent-picture">
          <img src={`/api/pictures/${picture.id}`} alt={`Picture you sent${pictures.length > 1 ? ` (${index + 1} of ${pictures.length})` : ''}`} width={picture.width} height={picture.height} loading="lazy" />
          {note && <figcaption className="link-note failed">{note}</figcaption>}
        </figure>
      })}
    </div>
  )
}
