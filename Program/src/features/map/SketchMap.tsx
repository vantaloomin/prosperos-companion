import { useEffect, useMemo, useRef } from 'react'
import { mainPin, pairs, sketch, type CityMapData } from './mapText'

interface Props { data: CityMapData; selected: string | null; onSelect: (id: string) => void; caption: string }

/** Fictional, original and private cities: soft neighbourhood shapes with their places inside, never fake streets. */
export function SketchMap({ data, selected, onSelect, caption }: Props) {
  const layout = useMemo(() => sketch(data), [data])
  const at = new Map(layout.bubbles.map((bubble) => [bubble.id, bubble]))
  const box = useRef<HTMLDivElement>(null)
  // Opens on the picked place, else their home, since a sketch is often bigger than the screen.
  useEffect(() => {
    const target = box.current?.querySelector('.sketch-pin.selected') ?? box.current?.querySelector('.sketch-pin.pin-home')
    target?.scrollIntoView({ block: 'center', inline: 'center' })
  }, [selected])
  return (
    <div ref={box} className="sketch-map">
      <p className="sketch-caption">{caption}</p>
      <svg viewBox={`0 0 ${layout.width} ${layout.height}`} style={{ width: layout.width, height: layout.height }} role="group" aria-label={`Sketch map of ${data.city.name}`}>
        {pairs(data.hoods).map(([first, second]) => {
          const a = at.get(first), b = at.get(second)
          if (!a || !b) return null
          // From edge to edge, so the dotted line joins the shapes without crossing them.
          const distance = Math.hypot(b.x - a.x, b.y - a.y) || 1, ux = (b.x - a.x) / distance, uy = (b.y - a.y) / distance
          return <line key={`${first}-${second}`} className="sketch-link" x1={a.x + ux * a.r} y1={a.y + uy * a.r} x2={b.x - ux * b.r} y2={b.y - uy * b.r} />
        })}
        {layout.bubbles.map((bubble, index) => (
          <g key={bubble.id}>
            <circle className={`sketch-hood tint-${index % 4}`} cx={bubble.x} cy={bubble.y} r={bubble.r} />
            <text className="sketch-name" x={bubble.x} y={bubble.y - bubble.r + 18}>{bubble.name}</text>
            {bubble.places.map(({ place, x, y }) => {
              const pin = mainPin(place)
              return (
                <g key={place.id} className={`sketch-pin map-pin pin-${pin}${place.id === selected ? ' selected' : ''}`} transform={`translate(${x - 7} ${y - 7})`}
                  role="button" tabIndex={-1} aria-label={place.name} onClick={() => onSelect(place.id)}>
                  <rect className="sketch-hit" x={-6} y={-6} width={26} height={26} />
                  <g className="sketch-glyph" transform="scale(0.6)"><PinShape pin={pin} /></g>
                  <title>{place.name}</title>
                </g>
              )
            })}
          </g>
        ))}
      </svg>
    </div>
  )
}

/** The same glyphs as the street map's pins (pins.ts), drawn inside the sketch. */
function PinShape({ pin }: { pin: ReturnType<typeof mainPin> }) {
  if (pin === 'home') return <path d="M4 11.5 12 5l8 6.5V20h-5v-5H9v5H4z" />
  if (pin === 'work') return <><rect x="4" y="8" width="16" height="11" rx="2" /><path d="M9 8V6.5A1.5 1.5 0 0 1 10.5 5h3A1.5 1.5 0 0 1 15 6.5V8" /></>
  return <circle cx="12" cy="12" r={pin === 'place' ? 4 : 6} />
}
