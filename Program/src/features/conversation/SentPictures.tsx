import { useState } from 'react'
import { Lightbox } from '../../components/Lightbox'
import type { Message } from '../../types'
import { pictureNote } from './pictureState'

/** The pictures you sent with a message, and a note when the companion could not see one. */
export function SentPictures({ message, name }: { message: Message; name: string }) {
  const pictures = message.pictures ?? []
  const [open, setOpen] = useState<number | null>(null)
  if (!pictures.length) return null
  const alt = (index: number) => `Picture you sent${pictures.length > 1 ? ` (${index + 1} of ${pictures.length})` : ''}`
  return (
    <div className="sent-pictures">
      {pictures.map((picture, index) => {
        const note = pictureNote(picture, name)
        return <figure key={picture.id} className="sent-picture">
          <button type="button" className="photo-open-inline" aria-label={`View full size: ${alt(index)}`} onClick={() => setOpen(index)}>
            <img src={`/api/pictures/${picture.id}`} alt={alt(index)} width={picture.width} height={picture.height} loading="lazy" />
          </button>
          {note && <figcaption className="link-note failed">{note}</figcaption>}
        </figure>
      })}
      {open !== null && <Lightbox pictures={pictures.map((picture, index) => ({ src: `/api/pictures/${picture.id}`, alt: alt(index), from: 'You', when: message.created_at }))} start={open} onClose={() => setOpen(null)} />}
    </div>
  )
}
