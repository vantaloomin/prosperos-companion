import { useReferences } from '../appearance/queries'
import { imageFile } from '../feed/imageState'
import { usePhoto } from './usePhoto'
import { usePortrait } from './portrait'

/**
 * The Visual novel style's stage: their profile picture, else their first appearance picture, or their initial when there is none yet,
 * in front of the latest photo they sent as the scene. The photo itself is in the reply too, with its description.
 */
export function NovelStage({ name, photoId }: { name: string; photoId: string | null }) {
  const references = useReferences()
  const portrait = usePortrait()
  const first = references.data?.references.find((reference) => reference.role !== 'excluded')
  const picture = portrait ?? (first ? `/api/lora/references/${first.id}/file` : null)
  const scene = usePhoto(photoId).data?.ref
  return (
    <div className="novel-stage" aria-hidden="true">
      {scene && <img className="novel-scene" src={imageFile(scene)} alt="" />}
      {picture ? <img src={picture} alt="" /> : <span className="novel-figure">{name.slice(0, 1).toUpperCase()}</span>}
    </div>
  )
}
