import type { MemeBox } from '../types'

/**
 * A meme's captions over its picture, as real text so it reads and scales: the classic top and bottom lines,
 * or a template's own text boxes (fractions of the picture, top to bottom) when it has them.
 */
export function MemeLines({ top, bottom, boxes }: { top?: string; bottom?: string; boxes?: MemeBox[] }) {
  if (boxes && boxes.length > 0) {
    return <>
      {[top, bottom].map((line, index) => line && boxes[index] ? (
        <span key={index} className="meme-text meme-box" style={{ left: `${boxes[index].x * 100}%`, top: `${boxes[index].y * 100}%`, width: `${boxes[index].w * 100}%`, height: `${boxes[index].h * 100}%` }}>{line}</span>
      ) : null)}
    </>
  }
  return <>
    {top && <span className="meme-text meme-top">{top}</span>}
    {bottom && <span className="meme-text meme-bottom">{bottom}</span>}
  </>
}
