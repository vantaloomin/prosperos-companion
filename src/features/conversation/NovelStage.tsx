import { useReferences } from '../appearance/queries'
import { imageFile } from '../feed/imageState'
import { usePhoto } from './usePhoto'

/**
 * The Visual novel style's stage: their first appearance picture, or their initial when there is none yet,
 * in front of the latest photo they sent as the scene. The photo itself is in the reply too, with its description.
 */
export function NovelStage({ name, photoId }: { name: string; photoId: string | null }) {
  const references = useReferences()
  const picture = references.data?.references.find((reference) => reference.role !== 'excluded')
  const scene = usePhoto(photoId).data?.ref
  return (
    <div className="novel-stage" aria-hidden="true">
      {scene && <img className="novel-scene" src={imageFile(scene)} alt="" />}
      {picture ? <img src={`/api/lora/references/${picture.id}/file`} alt="" /> : <span className="novel-figure">{name.slice(0, 1).toUpperCase()}</span>}
    </div>
  )
}
