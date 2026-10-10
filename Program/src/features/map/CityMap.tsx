import { lazy, Suspense, useState } from 'react'
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
  const picked = data.places.find((item) => item.id === selected) ?? null
  const street = data.city.real && !streetsFailed
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
      <div className="map-area">
        {asList ? <PlaceList places={data.places} onPick={(id) => { setSelected(id); setAsList(false) }} />
          : <MapView data={data} street={street} failed={streetsFailed} selected={selected} onSelect={setSelected} onFail={() => setStreetsFailed(true)} />}
        {picked && <PlaceCard place={picked} city={data.city.id} story={data.story} companion={companion} onClose={() => setSelected(null)} go={go} />}
      </div>
    </section>
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

/** The same places as a plain list by neighbourhood, for keyboards and screen readers. */
function PlaceList({ places, onPick }: { places: MapPlace[]; onPick: (id: string) => void }) {
  return (
    <div className="map-list">
      {byHood(places).map(([hood, items]) => (
        <section key={hood}>
          <h2>{hood}</h2>
          <ul>{items.map((item) => <li key={item.id}>
            <button type="button" className="text-button" onClick={() => onPick(item.id)}>{item.name}</button>
            <span className="subtle"> {item.kind}{item.pins.length ? ` · ${PIN_LABELS[mainPin(item)]}` : ''}</span>
          </li>)}</ul>
        </section>
      ))}
    </div>
  )
}
