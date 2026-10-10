import { useEffect, useId, useMemo, useRef } from 'react'
import { mainPin, type CityMapData, type MapPlace } from './mapText'
import { drawn, GROUNDS, lakeOutline, pathOf, type District, type Drawn } from './drawn'

interface Props { data: CityMapData; selected: string | null; onSelect: (id: string) => void; caption: string }

/** Fictional, original and private cities, or a street map that cannot load: a map drawn from the city data (drawn.ts). */
export function SketchMap({ data, selected, onSelect, caption }: Props) {
  const map = useMemo(() => drawn(data), [data])
  const box = useRef<HTMLDivElement>(null)
  const prefix = useId().replace(/:/g, '')
  // Opens on the picked place, else their home, since the map is often bigger than the screen.
  useEffect(() => {
    const target = box.current?.querySelector('.sketch-pin.selected') ?? box.current?.querySelector('.sketch-pin.pin-home')
    target?.scrollIntoView({ block: 'center', inline: 'center' })
  }, [selected])
  return (
    <div ref={box} className="sketch-map">
      <p className="sketch-caption">{caption}</p>
      <svg viewBox={`0 0 ${map.width} ${map.height}`} style={{ width: map.width, height: map.height }} role="group" aria-label={`Map of ${data.city.name}`}>
        <Ground map={map} prefix={prefix} />
        {map.districts.map((district) => district.places.map(({ place, x, y }) => (
          <PlacePin key={place.id} place={place} x={x} y={y} selected={place.id === selected} onSelect={onSelect} />
        )))}
        {map.districts.map((district) => district.places.filter(({ place }) => mainPin(place) !== 'place').map(({ place, x, y }) => (
          <text key={`${place.id}-name`} className="sketch-label" x={x + 17} y={y + 4} aria-hidden="true">{place.name}</text>
        )))}
      </svg>
    </div>
  )
}

/** Everything but the pins, dimmed like the street map's tiles. */
function Ground({ map, prefix }: { map: Drawn; prefix: string }) {
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
      {map.water.filter((water) => water.name).map((water) => <text key={`${water.name}-label`} className="drawn-water-name" x={water.label.x} y={water.label.y}>{water.name}</text>)}
      {map.districts.map((district) => <text key={`${district.id}-label`} className="drawn-name" x={district.label.x} y={district.label.y + 4}>{district.name}</text>)}
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

interface PinProps { place: MapPlace; x: number; y: number; selected: boolean; onSelect: (id: string) => void }

/** The same pins as the street map: a small dot for most places, a round badge with a glyph for theirs. */
function PlacePin({ place, x, y, selected, onSelect }: PinProps) {
  const pin = mainPin(place)
  return (
    <g className={`sketch-pin map-pin pin-${pin}${selected ? ' selected' : ''}`} transform={`translate(${x} ${y})`}
      role="button" tabIndex={-1} aria-label={place.name} onClick={() => onSelect(place.id)}>
      <circle className="sketch-hit" r={14} />
      {pin === 'place' ? <circle className="sketch-dot" r={4.5} /> : <>
        <circle className="sketch-badge" r={13} />
        <g className="sketch-glyph" transform="translate(-8 -8) scale(0.667)"><PinShape pin={pin} /></g>
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
