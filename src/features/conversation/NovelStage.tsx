import { useReferences } from '../appearance/queries'

/** The Visual novel style's stage: their first appearance picture, or their initial when there is none yet. */
export function NovelStage({ name }: { name: string }) {
  const references = useReferences()
  const picture = references.data?.references.find((reference) => reference.role !== 'excluded')
  return (
    <div className="novel-stage" aria-hidden="true">
      {picture ? <img src={`/api/lora/references/${picture.id}/file`} alt="" /> : <span className="novel-figure">{name.slice(0, 1).toUpperCase()}</span>}
    </div>
  )
}
