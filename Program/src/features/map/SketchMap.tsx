import { useEffect, useId, useMemo, useRef, useState, type RefObject } from 'react'
import { mainPin, narrow, type CityMapData, type MapPlace } from './mapText'
import { drawn, GROUNDS, labels, lakeOutline, pathOf, type District, type Drawn, type MapLabel } from './drawn'

/** `fit` shrinks the map to show the whole city where it can, as on the Draft Table, down to a size its names stay readable at. */
interface Props { data: CityMapData; selected: string | null; onSelect: (id: string) => void; caption: string; fit?: boolean }

/** Fictional, original and private cities, or a street map that cannot load: a map drawn from the city data (drawn.ts). */
export function SketchMap({ data, selected, onSelect, caption, fit = false }: Props) {
  const map = useMemo(() => drawn(data), [data])
  // Names placed so they do not run into each other (drawn.ts); a place's that does not fit shows on hover.
  const names = useMemo(() => new Map(labels(map).map((label) => [label.key, label])), [map])
  const box = useRef<HTMLDivElement>(null)
  const prefix = useId().replace(/:/g, '')
  const scale = useFit(box, map, fit)
  // Opens on the picked place, else their home, since the map is often bigger than the screen.
  useEffect(() => {
    const target = box.current?.querySelector('.sketch-pin.selected') ?? box.current?.querySelector('.sketch-pin.pin-home')
    target?.scrollIntoView({ block: 'center', inline: 'center' })
    // On a phone the card is a sheet over the lower part, so the picked place moves up above it.
    if (selected && narrow() && box.current) box.current.scrollBy({ top: box.current.clientHeight * 0.28 })
  }, [selected])
  return (
    <div ref={box} className={`sketch-map${fit ? ' fit' : ''}`}>
      <p className="sketch-caption">{caption}</p>
      <svg viewBox={`0 0 ${map.width} ${map.height}`} style={{ width: map.width * scale, height: map.height * scale }} role="group" aria-label={`Map of ${data.city.name}`}>
        <Ground map={map} prefix={prefix} names={names} />
        {map.districts.map((district) => district.places.map(({ place, x, y }) => (
          <PlacePin key={place.id} place={place} x={x} y={y} named={names.get(`${place.id}-name`)?.shown ?? false} selected={place.id === selected} onSelect={onSelect} />
        )))}
        {[...names.values()].filter((label) => label.kind === 'place' && label.shown).map((label) => <Name key={label.key} label={label} className="sketch-label" />)}
      </svg>
    </div>
  )
}

const SMALLEST = 0.7
const CAPTION = 34

/** How much to shrink the map to fit its box, kept up to date as the window changes. */
function useFit(box: RefObject<HTMLDivElement | null>, map: { width: number; height: number }, fit: boolean): number {
  const [size, setSize] = useState<{ width: number; height: number } | null>(null)
  useEffect(() => {
    const element = box.current
    if (!fit || !element || typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(() => setSize({ width: element.clientWidth, height: element.clientHeight - CAPTION }))
    observer.observe(element)
    return () => observer.disconnect()
  }, [box, fit])
  if (!fit || !size) return 1
  return Math.min(1, Math.max(SMALLEST, Math.min(size.width / map.width, size.height / map.height)))
}

/** Everything but the pins, dimmed like the street map's tiles. */
function Ground({ map, prefix, names }: { map: Drawn; prefix: string; names: Map<string, MapLabel> }) {
  return (
    <g className="drawn-ground" aria-hidden="true">
      <rect className="drawn-country" width={map.width} height={map.height} />
      {map.water.filter((water) => water.kind === 'sea').map((water) => <path key={water.name} className="drawn-water" d={pathOf(water.path, true)} />)}
      {map.outskirts.map((outline, index) => <path key={index} className="drawn-outskirts" d={pathOf(outline, true)} />)}
      {map.districts.map((district, index) => <DistrictShape key={district.id} district={district} tint={index % 4} clip={`${prefix}-${district.id}`} />)}
      {map.water.filter((water) => water.kind === 'river').map((water) => (
        <path key={water.name} className="drawn-river" d={pathOf(water.path, false, true)} style={{ strokeWidth: water.width }} />
      ))}
      {map.water.filter((water) => water.kind === 'lake').map((water) => <path key={water.name} className="drawn-water" d={pathOf(lakeOutline(water), true)} />)}
      {map.roads.map((road) => <path key={`${road.id}-casing`} className="drawn-road-casing" d={`M${road.from.x} ${road.from.y}Q${road.via.x} ${road.via.y} ${road.to.x} ${road.to.y}`} />)}
      {map.roads.map((road) => <path key={road.id} className="drawn-road" d={`M${road.from.x} ${road.from.y}Q${road.via.x} ${road.via.y} ${road.to.x} ${road.to.y}`} />)}
      {[...names.values()].filter((label) => label.kind === 'water' && label.shown).map((label) => <Name key={label.key} label={label} className="drawn-water-name" />)}
      {[...names.values()].filter((label) => label.kind === 'district').map((label) => <Name key={label.key} label={label} className="drawn-name" />)}
    </g>
  )
}

/** One neighbourhood: its ground, side streets and parks cut to its outline, and a dashed border. */
function DistrictShape({ district, tint, clip }: { district: District; tint: number; clip: string }) {
  const outline = pathOf(district.outline, true)
  return (
    <g>
      <clipPath id={clip}><path d={outline} /></clipPath>
      <path className={`drawn-land tint-${tint}`} d={outline} />
      <g clipPath={`url(#${clip})`}>
        {district.streets.map(([a, b], index) => <line key={index} className="drawn-street" x1={a.x} y1={a.y} x2={b.x} y2={b.y} />)}
        {district.places.filter(({ place }) => GROUNDS[place.kind]).map(({ place, x, y }) => (
          <rect key={place.id} className={`drawn-${GROUNDS[place.kind]}`} x={x - 13} y={y - 13} width={26} height={26} rx={5} />
        ))}
      </g>
      <path className="drawn-border" d={outline} />
    </g>
  )
}

function Name({ label, className }: { label: MapLabel; className: string }) {
  return <text className={className} x={label.x} y={label.y} style={{ textAnchor: label.anchor }} aria-hidden="true">{label.text}</text>
}

interface PinProps { place: MapPlace; x: number; y: number; named: boolean; selected: boolean; onSelect: (id: string) => void }

/** The same pins as the street map: a small dot for most places, a round badge with a glyph for theirs. */
function PlacePin({ place, x, y, named, selected, onSelect }: PinProps) {
  const pin = mainPin(place)
  return (
    <g className={`sketch-pin map-pin pin-${pin}${selected ? ' selected' : ''}`} transform={`translate(${x} ${y})`}
      role="button" tabIndex={0} aria-label={place.name} onClick={() => onSelect(place.id)}
      onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(place.id) } }}>
      <circle className="sketch-hit" r={14} />
      {pin === 'place' ? <><circle className="sketch-dot" r={4.5} /><text className="sketch-label sketch-hover-label" x={9} y={4}>{place.name}</text></> : <>
        <circle className="sketch-badge" r={13} />
        <g className="sketch-glyph" transform="translate(-8 -8) scale(0.667)"><PinShape pin={pin} /></g>
        {!named && <text className="sketch-label sketch-hover-label" x={17} y={4}>{place.name}</text>}
      </>}
      <title>{place.name}</title>
    </g>
  )
}

/** The same glyphs as the street map's pins (pins.ts). */
function PinShape({ pin }: { pin: ReturnType<typeof mainPin> }) {
  if (pin === 'home') return <path d="M4 11.5 12 5l8 6.5V20h-5v-5H9v5H4z" />
  if (pin === 'work') return <><rect x="4" y="8" width="16" height="11" rx="2" /><path d="M9 8V6.5A1.5 1.5 0 0 1 10.5 5h3A1.5 1.5 0 0 1 15 6.5V8" /></>
  return <circle cx="12" cy="12" r="6" />
}
