import { lazy, Suspense, useEffect, useRef, useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, KeyRound, List, Map as MapIcon } from 'lucide-react'
import { api } from '../../api'
import type { View } from '../../companion'
import type { Companion } from '../../types'
import { Loading } from '../../components/Feedback'
import { ErrorNotice } from '../../components/ErrorNotice'
import { PlaceCard } from './PlaceCard'
import { SketchMap } from './SketchMap'
import { byHood, mainPin, PIN_LABELS, type CityMapData, type MapPlace, type Pin } from './mapText'
import { pinMarkup } from './pins'

// Leaflet and its street tiles load only for a real city.
const StreetMap = lazy(() => import('./StreetMap').then((m) => ({ default: m.StreetMap })))

/**
 * The city map (Hit List #40): where they live, work and go, and every place in their city to click. A real
 * city gets a street map; fictional, original and private cities, or a street map that cannot load, a drawn map
 * of the neighbourhoods. Opened from Today, Story mode and "Show on map" links; never shows where you are.
 */
export function CityMap({ companion, place, go }: { companion: Companion; place: string | null; go: (view: View) => void }) {
  const map = useQuery({ queryKey: ['city-map'], queryFn: () => api<CityMapData>('/life/map') })
  const [selected, setSelected] = useState<string | null>(place)
  const [asList, setAsList] = useState(false)
  const [streetsFailed, setStreetsFailed] = useState(false)
  if (map.isPending) return <Loading label="Unfolding the map" />
  if (map.isError) return <section className="page"><ErrorNotice error={map.error} /></section>
  const data = map.data
  return (
    <section className="map-page" aria-labelledby="map-title">
      <header className="map-bar">
        <button type="button" className="icon-button" aria-label="Back" onClick={() => window.history.length > 1 ? window.history.back() : go('today')}><ArrowLeft aria-hidden="true" /></button>
        <h1 id="map-title">{data.city.name}</h1>
        <MapKey />
        <button type="button" className="button" aria-pressed={asList} onClick={() => setAsList(!asList)}>
          {asList ? <MapIcon aria-hidden="true" /> : <List aria-hidden="true" />}{asList ? 'Map' : 'List'}
        </button>
      </header>
      <MapArea data={data} asList={asList} selected={selected} onSelect={setSelected} streetsFailed={streetsFailed} onFail={() => setStreetsFailed(true)} companion={companion} go={go} />
    </section>
  )
}

interface AreaProps { data: CityMapData; asList: boolean; selected: string | null; onSelect: (id: string | null) => void; streetsFailed: boolean; onFail: () => void; companion: Companion; go: (view: View) => void }

/** The map or the list, and the picked place's card: floating over the map, or opened in its row in the list. */
function MapArea({ data, asList, selected, onSelect, streetsFailed, onFail, companion, go }: AreaProps) {
  const picked = data.places.find((item) => item.id === selected) ?? null
  const card = (inline: boolean) => picked && <PlaceCard inline={inline} place={picked} city={data.city.id} story={data.story} companion={companion} onClose={() => onSelect(null)} go={go} />
  return (
    <div className="map-area">
      {asList ? <PlaceList places={data.places} selected={selected} onPick={(id) => onSelect(id === selected ? null : id)} card={card(true)} />
        : <MapView data={data} street={data.city.real && !streetsFailed} failed={streetsFailed} selected={selected} onSelect={onSelect} onFail={onFail} />}
      {!asList && card(false)}
    </div>
  )
}

interface ViewProps { data: CityMapData; street: boolean; failed: boolean; selected: string | null; onSelect: (id: string) => void; onFail: () => void }

function MapView({ data, street, failed, selected, onSelect, onFail }: ViewProps) {
  if (street) return <Suspense fallback={<Loading label="Loading the street map" />}><StreetMap data={data} selected={selected} onSelect={onSelect} onFail={onFail} /></Suspense>
  const caption = failed ? `Couldn't load the street map, so this is a drawn map of ${data.city.name}. Neighbourhoods are placed by how they connect, not to scale.`
    : 'Drawn map. Neighbourhoods are placed by how they connect, not to scale.'
  return <SketchMap data={data} selected={selected} onSelect={onSelect} caption={caption} />
}

function MapKey() {
  const [open, setOpen] = useState(false)
  // No work pin yet: companions have no set workplace (companion/life/citymap.py).
  const pins: (Pin | 'place')[] = ['home', 'usual', 'recent', 'scene', 'place']
  return (
    <div className="map-key">
      <button type="button" className="button" aria-expanded={open} onClick={() => setOpen(!open)}><KeyRound aria-hidden="true" />Key</button>
      {open && <ul className="map-key-card">
        {pins.map((pin) => <li key={pin}><span className={`map-pin pin-${pin}`} dangerouslySetInnerHTML={{ __html: pinMarkup(pin) }} />{PIN_LABELS[pin]}</li>)}
      </ul>}
    </div>
  )
}

/** The same places as a plain list by neighbourhood, for keyboards and screen readers; the picked one opens in its row. */
function PlaceList({ places, selected, onPick, card }: { places: MapPlace[]; selected: string | null; onPick: (id: string) => void; card: ReactNode }) {
  const box = useRef<HTMLDivElement>(null)
  // Opens on the picked place's row, carried over from the map.
  useEffect(() => { box.current?.querySelector('li.picked')?.scrollIntoView({ block: 'start' }) }, [])
  return (
    <div ref={box} className="map-list">
      {byHood(places).map(([hood, items]) => (
        <section key={hood}>
          <h2>{hood}</h2>
          <ul>{items.map((item) => <li key={item.id} className={item.id === selected ? 'picked' : undefined}>
            <button type="button" className="text-button" aria-expanded={item.id === selected} onClick={() => onPick(item.id)}>{item.name}</button>
            <span className="subtle"> {item.kind}{item.pins.length ? ` · ${PIN_LABELS[mainPin(item)]}` : ''}</span>
            {item.id === selected && card}
          </li>)}</ul>
        </section>
      ))}
    </div>
  )
}
