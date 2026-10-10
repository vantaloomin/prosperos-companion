import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { mainPin, type CityMapData } from './mapText'
import { pinMarkup } from './pins'

interface Props { data: CityMapData; selected: string | null; onSelect: (id: string) => void; onFail: () => void }

// A street map that keeps failing (offline, blocked) gives way to the sketch.
const FAILED_TILES = 6

/** Real public cities: OpenStreetMap tiles with their attribution, and the places as pins. */
export function StreetMap({ data, selected, onSelect, onFail }: Props) {
  const box = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  const markers = useRef(new Map<string, L.Marker>())
  // The map is built once per city data; the latest callbacks are read through refs so a render never rebuilds it.
  const callbacks = useRef({ onSelect, onFail })
  useEffect(() => { callbacks.current = { onSelect, onFail } }, [onSelect, onFail])
  useEffect(() => {
    if (!box.current) return
    const created = L.map(box.current, { zoomControl: true, attributionControl: true }).setView([data.city.lat, data.city.lon], 13)
    let failures = 0
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).on('tileerror', () => { failures += 1; if (failures === FAILED_TILES) callbacks.current.onFail() }).addTo(created)
    for (const place of data.places) {
      const pin = mainPin(place)
      const icon = L.divIcon({ className: `map-pin pin-${pin}`, html: pinMarkup(pin), iconSize: pin === 'place' ? [12, 12] : [26, 26] })
      const marker = L.marker([place.lat, place.lon], { icon, title: place.name, keyboard: true, zIndexOffset: pin === 'place' ? 0 : 500 })
        .on('click', () => callbacks.current.onSelect(place.id)).addTo(created)
      markers.current.set(place.id, marker)
    }
    const marked = data.places.filter((place) => place.pins.length)
    if (marked.length > 1) created.fitBounds(L.latLngBounds(marked.map((place) => [place.lat, place.lon])), { padding: [60, 60], maxZoom: 14 })
    map.current = created
    const found = markers.current
    return () => { created.remove(); found.clear(); map.current = null }
  }, [data])
  useEffect(() => {
    for (const [id, marker] of markers.current) marker.getElement()?.classList.toggle('selected', id === selected)
    const marker = selected ? markers.current.get(selected) : null
    if (marker && map.current) map.current.panTo(marker.getLatLng())
  }, [selected])
  return <div ref={box} className="street-map" />
}
