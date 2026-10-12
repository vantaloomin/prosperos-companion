/**
 * The drawn map for cities without a street map (fictional, original and private ones, or when tiles fail): the
 * same look as the street map, drawn from the city data alone. Each neighbourhood is a district shaped by its
 * neighbours (a weighted Voronoi cell, cut to a wobbly coastline), with a seeded grid of side streets, main roads
 * to the districts next to it, parks under green places, and any sea, river or lake the city data names. Places
 * sit on street corners. Not to scale, and the caption says so.
 */
import { mainPin, type CityMapData, type MapPlace, type MapWater, type Pin } from './mapText.ts'

export interface Point { x: number; y: number }
export interface District { id: string; name: string; x: number; y: number; outline: Point[]; streets: [Point, Point][]; label: Point; places: { place: MapPlace; x: number; y: number }[] }
export interface Road { id: string; from: Point; via: Point; to: Point }
export interface DrawnWater { kind: MapWater['kind']; name: string; path: Point[]; width: number; label: Point }
export interface Drawn { width: number; height: number; districts: District[]; roads: Road[]; water: DrawnWater[]; outskirts: Point[][] }

const GAP = 18
const MARGIN = 50
const SEA = 150
const STREET = 32
const SIDES = 56

/** A number in [0, 1) from text, the same every time (FNV-1a). */
export function unit(text: string): number {
  let hash = 2166136261
  for (let index = 0; index < text.length; index++) hash = Math.imul(hash ^ text.charCodeAt(index), 16777619)
  return (hash >>> 0) / 4294967296
}

interface Seat { id: string; name: string; x: number; y: number; r: number; homeX: number; homeY: number }

export function drawn(data: CityMapData): Drawn {
  if (!data.hoods.length) return { width: 400, height: 300, districts: [], roads: [], water: [], outskirts: [] }
  const { seats, project, perKm } = place(data)
  const sea = data.water?.filter((water) => water.kind === 'sea') ?? []
  const shift = frame(seats, sea)
  const move = (point: Point): Point => drift(seats, point, shift)
  const districts = seats.map((seat) => district(seat, seats, data.places.filter((item) => item.hood_id === seat.id)))
  const water = (data.water ?? []).map((item) => waterShape(item, seats, project, move, perKm, shift))
  const labels = districts.map((district) => district.label)
  return { width: shift.width, height: shift.height, districts, roads: roads(seats, districts), water: water.map((item) => clearLabel(item, labels)), outskirts: seats.map((seat) => outskirts(seat, seats)) }
}

/**
 * Neighbourhoods where the city data puts them, scaled so close neighbours sit side by side, with far-out ones
 * pulled in (a gentle log squeeze past a few neighbour-lengths), then pushed apart until each has room for its places.
 */
function place(data: CityMapData) {
  const squash = Math.cos((data.city.lat * Math.PI) / 180)
  const km = (lat: number, lon: number): Point => ({ x: lon * squash * 111, y: -lat * 111 })
  const raw = data.hoods.map((hood) => km(hood.lat, hood.lon))
  const centre = { x: raw.reduce((sum, at) => sum + at.x, 0) / raw.length, y: raw.reduce((sum, at) => sum + at.y, 0) / raw.length }
  const sizes = data.hoods.map((hood) => radiusFor(data.places.filter((item) => item.hood_id === hood.id).length))
  const typical = quartile(raw.map((at, index) => Math.min(...raw.filter((_, other) => other !== index).map((other) => Math.hypot(other.x - at.x, other.y - at.y))))) || 0.5
  const perKm = ((2 * sizes.reduce((sum, size) => sum + size, 0)) / sizes.length + GAP) / typical, reach = typical * 2.5
  const project = (lat: number, lon: number): Point => {
    const at = km(lat, lon), dx = at.x - centre.x, dy = at.y - centre.y, distance = Math.hypot(dx, dy)
    const squeeze = distance <= reach ? 1 : (reach + reach * Math.log(distance / reach)) / distance
    return { x: dx * squeeze * perKm, y: dy * squeeze * perKm }
  }
  const seats: Seat[] = data.hoods.map((hood, index) => {
    const at = project(hood.lat, hood.lon)
    return { id: hood.id, name: hood.name, ...at, homeX: at.x, homeY: at.y, r: sizes[index] }
  })
  separate(seats)
  return { seats, project, perKm }
}

function radiusFor(count: number): number {
  return Math.max(52, Math.sqrt(count) * STREET * 0.8 + 30)
}

/** The lower quartile: scaling by the closer neighbours keeps the town tight, and pushing apart makes the room. */
function quartile(values: number[]): number {
  const sorted = values.filter(Number.isFinite).sort((a, b) => a - b)
  return sorted.length ? sorted[Math.floor(sorted.length / 4)] : 0
}

function separate(seats: Seat[]) {
  for (let round = 0; round < 300; round++) {
    let moved = false
    for (const a of seats) for (const b of seats) if (a !== b && pushApart(a, b)) moved = true
    if (!moved) return
  }
}

function pushApart(a: Seat, b: Seat): boolean {
  const dx = b.x - a.x || 0.1, dy = b.y - a.y || 0.1, distance = Math.hypot(dx, dy), need = a.r + b.r + GAP
  if (distance >= need) return false
  const push = (need - distance) / 2
  a.x -= (dx / distance) * push; a.y -= (dy / distance) * push
  b.x += (dx / distance) * push; b.y += (dy / distance) * push
  return true
}

interface Frame { dx: number; dy: number; width: number; height: number; sea: Set<string> }

/** Moves everything into view with a margin, and room for the sea on its side. */
function frame(seats: Seat[], sea: MapWater[]): Frame {
  const sides = new Set(sea.map((item) => item.side ?? 'south'))
  const reach = (seat: Seat) => reachOf(seat, seats)
  const left = Math.min(...seats.map((seat) => seat.x - reach(seat))) - MARGIN - (sides.has('west') ? SEA : 0)
  const top = Math.min(...seats.map((seat) => seat.y - reach(seat))) - MARGIN - (sides.has('north') ? SEA : 0)
  for (const seat of seats) { seat.x -= left; seat.y -= top; seat.homeX -= left; seat.homeY -= top }
  const width = Math.max(...seats.map((seat) => seat.x + reach(seat))) + MARGIN + (sides.has('east') ? SEA : 0)
  const height = Math.max(...seats.map((seat) => seat.y + reach(seat))) + MARGIN + (sides.has('south') ? SEA : 0)
  return { dx: -left, dy: -top, width, height, sea: sides }
}

/** How far a district may reach: enough for its places, and past the halfway line to its nearest neighbour. */
function reachOf(seat: Seat, seats: Seat[]): number {
  const nearest = Math.min(...seats.filter((other) => other !== seat).map((other) => Math.hypot(other.x - seat.x, other.y - seat.y)))
  // Capped, so a far-off neighbourhood stays its own size instead of spreading over empty country.
  return Math.max(seat.r * 1.45, Number.isFinite(nearest) ? Math.min(nearest * 0.62, seat.r * 2.4) : 0)
}

/** A point given in the city's own coordinates, moved the way the neighbourhoods near it were moved. */
function drift(seats: Seat[], point: Point, shift: Frame): Point {
  const at = { x: point.x + shift.dx, y: point.y + shift.dy }
  let total = 0, x = 0, y = 0
  for (const seat of seats) {
    const weight = 1 / (Math.hypot(seat.homeX - at.x, seat.homeY - at.y) ** 2 + 1)
    total += weight; x += weight * (seat.x - seat.homeX); y += weight * (seat.y - seat.homeY)
  }
  return { x: at.x + x / total, y: at.y + y / total }
}

function district(seat: Seat, seats: Seat[], places: MapPlace[]): District {
  let outline = coast(seat, reachOf(seat, seats))
  for (const other of seats) if (other !== seat) outline = cut(outline, seat, other)
  const label = { x: seat.x, y: seat.y }
  const { streets, corners } = grid(seat, outline, places.length, label)
  return { id: seat.id, name: seat.name, x: seat.x, y: seat.y, outline, streets, label, places: places.map((item, index) => ({ place: item, ...corners[index] })) }
}

/** The edge of town around a district, wider than the district itself, so gaps between neighbourhoods read as town. */
function outskirts(seat: Seat, seats: Seat[]): Point[] {
  const nearest = Math.min(...seats.filter((other) => other !== seat).map((other) => Math.hypot(other.x - seat.x, other.y - seat.y)))
  const reach = reachOf(seat, seats)
  return coast(seat, Math.max(reach * 1.25, Number.isFinite(nearest) ? Math.min(nearest * 0.85, seat.r * 3.4) : 0))
}

/** A wobbly round edge, the same for a neighbourhood every time. */
function coast(seat: Seat, reach: number): Point[] {
  const phase = unit(`${seat.id}:coast`) * Math.PI * 2, wobble = 0.06 + unit(`${seat.id}:wobble`) * 0.06
  return Array.from({ length: SIDES }, (_, index) => {
    const angle = (index / SIDES) * Math.PI * 2
    const bend = 1 + wobble * (Math.sin(angle * 3 + phase) * 0.6 + Math.sin(angle * 7 + phase * 2) * 0.4)
    return { x: seat.x + Math.cos(angle) * reach * bend, y: seat.y + Math.sin(angle) * reach * bend }
  })
}

/** Keeps the part of the outline nearer to this neighbourhood than to the other, weighted so busier ones get more room. */
function cut(outline: Point[], seat: Seat, other: Seat): Point[] {
  const nx = other.x - seat.x, ny = other.y - seat.y
  const limit = (other.x ** 2 + other.y ** 2 - seat.x ** 2 - seat.y ** 2 + seat.r ** 2 - other.r ** 2) / 2
  const side = (point: Point) => point.x * nx + point.y * ny - limit
  const kept: Point[] = []
  outline.forEach((point, index) => {
    const next = outline[(index + 1) % outline.length]
    const here = side(point), there = side(next)
    if (here <= 0) kept.push(point)
    if ((here <= 0) !== (there <= 0)) {
      const share = here / (here - there)
      kept.push({ x: point.x + (next.x - point.x) * share, y: point.y + (next.y - point.y) * share })
    }
  })
  return kept
}

export function inside(point: Point, outline: Point[]): boolean {
  let found = false
  for (let index = 0, last = outline.length - 1; index < outline.length; last = index++) {
    const a = outline[index], b = outline[last]
    if ((a.y > point.y) !== (b.y > point.y) && point.x < ((b.x - a.x) * (point.y - a.y)) / (b.y - a.y) + a.x) found = !found
  }
  return found
}

function edgeDistance(point: Point, outline: Point[]): number {
  let best = Infinity
  outline.forEach((a, index) => {
    const b = outline[(index + 1) % outline.length]
    const length = Math.hypot(b.x - a.x, b.y - a.y) || 1
    const along = Math.max(0, Math.min(1, ((point.x - a.x) * (b.x - a.x) + (point.y - a.y) * (b.y - a.y)) / length ** 2))
    best = Math.min(best, Math.hypot(point.x - (a.x + (b.x - a.x) * along), point.y - (a.y + (b.y - a.y) * along)))
  })
  return best
}

/** Side streets at a seeded angle, and the corners places sit on, nearest the middle first, clear of the name. */
function grid(seat: Seat, outline: Point[], count: number, label: Point) {
  const angle = (unit(`${seat.id}:angle`) - 0.5) * 0.7
  let step = STREET, corners: Point[] = []
  for (let tries = 0; tries < 5; tries++, step *= 0.82) {
    corners = cornersIn(seat, outline, angle, step, label)
    if (corners.length >= count) break
  }
  while (corners.length < count) corners.push({ x: seat.x + (corners.length % 3) * 6, y: seat.y + 18 })
  return { streets: streetLines(seat, angle, step), corners }
}

function turn(seat: Seat, angle: number, u: number, v: number): Point {
  return { x: seat.x + u * Math.cos(angle) - v * Math.sin(angle), y: seat.y + u * Math.sin(angle) + v * Math.cos(angle) }
}

function cornersIn(seat: Seat, outline: Point[], angle: number, step: number, label: Point): Point[] {
  const span = Math.ceil((seat.r * 3) / step), found: Point[] = []
  const halfWidth = seat.name.length * 3.6 + 8
  for (let u = -span; u <= span; u++) for (let v = -span; v <= span; v++) {
    const point = turn(seat, angle, (u + 0.5) * step, (v + 0.5) * step)
    const onLabel = Math.abs(point.x - label.x) < halfWidth && Math.abs(point.y - label.y) < 14
    if (!onLabel && inside(point, outline) && edgeDistance(point, outline) > 10) found.push(point)
  }
  return found.sort((a, b) => Math.hypot(a.x - seat.x, a.y - seat.y) - Math.hypot(b.x - seat.x, b.y - seat.y))
}

/** Long lines both ways across the district; the drawing clips them to its outline. */
function streetLines(seat: Seat, angle: number, step: number): [Point, Point][] {
  const span = Math.ceil((seat.r * 3) / step), far = (span + 1) * step, lines: [Point, Point][] = []
  for (let index = -span; index <= span; index++) {
    lines.push([turn(seat, angle, (index + 0.5) * step, -far), turn(seat, angle, (index + 0.5) * step, far)])
    lines.push([turn(seat, angle, -far, (index + 0.5) * step), turn(seat, angle, far, (index + 0.5) * step)])
  }
  return lines
}

/** A main road between each pair of neighbourhoods that share a border, with a gentle seeded bend. */
function roads(seats: Seat[], districts: District[]): Road[] {
  const found: Road[] = []
  seats.forEach((a, index) => seats.slice(index + 1).forEach((b, offset) => {
    if (touching(a, b, districts[index].outline, districts[index + 1 + offset].outline)) found.push(road(a, b))
  }))
  // A neighbourhood on its own still gets a road out, to the nearest one.
  for (const seat of seats) {
    if (seats.length < 2 || found.some((item) => item.id.split('|').includes(seat.id))) continue
    const nearest = seats.filter((other) => other !== seat).reduce((best, other) => Math.hypot(other.x - seat.x, other.y - seat.y) < Math.hypot(best.x - seat.x, best.y - seat.y) ? other : best)
    found.push(road(seat, nearest))
  }
  return found
}

function road(a: Seat, b: Seat): Road {
  const id = [a.id, b.id].sort().join('|'), bend = (unit(`${id}:bend`) - 0.5) * 0.25
  const via = { x: (a.x + b.x) / 2 - (b.y - a.y) * bend, y: (a.y + b.y) / 2 + (b.x - a.x) * bend }
  return { id, from: { x: a.x, y: a.y }, via, to: { x: b.x, y: b.y } }
}

/** Whether the line between two centres crosses straight from one district into the other. */
function touching(a: Seat, b: Seat, first: Point[], second: Point[]): boolean {
  const length = Math.hypot(b.x - a.x, b.y - a.y) || 1, ux = (b.x - a.x) / length, uy = (b.y - a.y) / length
  // Where the weighted halfway line crosses the segment, from the same sum as cut().
  const along = (length ** 2 + a.r ** 2 - b.r ** 2) / (2 * length)
  const near = (shift: number): Point => ({ x: a.x + ux * (along + shift), y: a.y + uy * (along + shift) })
  return inside(near(-4), first) && inside(near(4), second)
}

function waterShape(item: MapWater, seats: Seat[], project: (lat: number, lon: number) => Point, move: (point: Point) => Point, perKm: number, shift: Frame): DrawnWater {
  if (item.kind === 'sea') return seaShape(item, seats, shift)
  const points = item.points.map(([lat, lon]) => move(project(lat, lon)))
  // A river runs on past the ends it was given, off the edge of the map.
  const path = item.kind === 'river' ? [beyond(points[1], points[0]), ...points, beyond(points[points.length - 2], points[points.length - 1])] : points
  const width = Math.min(item.kind === 'lake' ? 150 : 34, Math.max(item.kind === 'lake' ? 36 : 12, item.width_km * perKm))
  const middle = path[Math.floor(path.length / 2)] ?? { x: 0, y: 0 }
  return { kind: item.kind, name: item.name, path, width, label: item.kind === 'lake' ? middle : { x: middle.x, y: middle.y - width / 2 - 6 } }
}

function beyond(from: Point, to: Point): Point {
  const length = Math.hypot(to.x - from.x, to.y - from.y) || 1
  return { x: to.x + ((to.x - from.x) / length) * 400, y: to.y + ((to.y - from.y) / length) * 400 }
}

/** A river's name goes where it is furthest from any neighbourhood's name. */
function clearLabel(water: DrawnWater, labels: Point[]): DrawnWater {
  if (water.kind !== 'river' || water.path.length < 4) return water
  const room = (point: Point) => Math.min(...labels.map((label) => Math.hypot(label.x - point.x, (label.y - point.y) * 2)))
  const candidates = water.path.slice(2, -1).map((point, index) => ({ x: (point.x + water.path[index + 1].x) / 2, y: (point.y + water.path[index + 1].y) / 2 }))
  const best = candidates.reduce((most, point) => room(point) > room(most) ? point : most)
  return { ...water, label: { x: best.x, y: best.y - water.width / 2 - 6 } }
}

/** The sea beyond the city's middle on its side: districts drawn over it make the coastline. */
function seaShape(item: MapWater, seats: Seat[], shift: Frame): DrawnWater {
  const side = item.side ?? 'south'
  const middle = { x: seats.reduce((sum, seat) => sum + seat.x, 0) / seats.length, y: seats.reduce((sum, seat) => sum + seat.y, 0) / seats.length }
  const { width: w, height: h } = shift
  const boxes = {
    south: [{ x: 0, y: middle.y }, { x: w, y: middle.y }, { x: w, y: h }, { x: 0, y: h }],
    north: [{ x: 0, y: 0 }, { x: w, y: 0 }, { x: w, y: middle.y }, { x: 0, y: middle.y }],
    east: [{ x: middle.x, y: 0 }, { x: w, y: 0 }, { x: w, y: h }, { x: middle.x, y: h }],
    west: [{ x: 0, y: 0 }, { x: middle.x, y: 0 }, { x: middle.x, y: h }, { x: 0, y: h }],
  }
  const labels = { south: { x: w / 2, y: h - SEA / 2 }, north: { x: w / 2, y: SEA / 2 }, east: { x: w - SEA / 2, y: h / 2 }, west: { x: SEA / 2, y: h / 2 } }
  return { kind: 'sea', name: item.name, path: boxes[side], width: 0, label: labels[side] }
}

/** An SVG path through the points: straight for an outline, smooth (Catmull-Rom) for a river. */
export function pathOf(points: Point[], closed: boolean, smooth = false): string {
  if (!points.length) return ''
  const fixed = (point: Point) => `${point.x.toFixed(1)} ${point.y.toFixed(1)}`
  if (!smooth || points.length < 3) return `M${points.map(fixed).join('L')}${closed ? 'Z' : ''}`
  let d = `M${fixed(points[0])}`
  for (let index = 0; index < points.length - 1; index++) {
    const p0 = points[index - 1] ?? points[index], p1 = points[index], p2 = points[index + 1], p3 = points[index + 2] ?? p2
    const c1 = { x: p1.x + (p2.x - p0.x) / 6, y: p1.y + (p2.y - p0.y) / 6 }, c2 = { x: p2.x - (p3.x - p1.x) / 6, y: p2.y - (p3.y - p1.y) / 6 }
    d += `C${fixed(c1)} ${fixed(c2)} ${fixed(p2)}`
  }
  return d
}

/** A lake: a wobbly round shape around its centre. */
export function lakeOutline(water: DrawnWater): Point[] {
  const centre = water.path[0] ?? { x: 0, y: 0 }, phase = unit(`${water.name}:lake`) * Math.PI * 2
  return Array.from({ length: 32 }, (_, index) => {
    const angle = (index / 32) * Math.PI * 2, bend = 1 + 0.12 * Math.sin(angle * 3 + phase)
    return { x: centre.x + Math.cos(angle) * water.width * bend, y: centre.y + Math.sin(angle) * water.width * 0.7 * bend }
  })
}

/** A name on the drawn map, where it fits; a place's or water's that fits nowhere is left off (a place's then shows on hover). */
export interface MapLabel { key: string; kind: 'district' | 'water' | 'place'; text: string; x: number; y: number; anchor: 'start' | 'middle' | 'end'; shown: boolean }
interface Box { x: number; y: number; w: number; h: number; weight?: number }

// Rough text widths per letter at each label's size (styles.css), since the layout runs before anything is measured.
const LETTER = { district: 8, water: 8, place: 6.6 }
// How far each kind's text reaches above and below the baseline.
const INK = { district: [10, 2], water: [12, 4], place: [11, 3] } as const
// After the neighbourhoods, their home, work and the scene claim their spot first, then their other places, then water.
const RANK: Record<Pin, number> = { scene: 0, home: 0, work: 0, usual: 1, recent: 2 }

/**
 * Keeps names from running into each other and into pins. Neighbourhood names go first and are never left off:
 * each moves straight up or down off any pin sitting on it, staying in its neighbourhood, to the least crowded spot. Then every other name, most
 * important first, takes the first spot next to where it belongs that is clear of the names already placed and of
 * the pins' badges, or is left off (a place's name then shows on hover).
 */
export function labels(map: Drawn): MapLabel[] {
  const spots = map.districts.flatMap((district) => district.places)
  const pinned = spots.filter(({ place }) => mainPin(place) !== 'place')
  // Covering a plain dot matters less than covering a badge or another name.
  const dots: Box[] = spots.filter(({ place }) => mainPin(place) === 'place').map(({ x, y }) => ({ x: x - 5, y: y - 5, w: 10, h: 10, weight: 1 }))
  const badges: Box[] = pinned.map(({ x, y }) => ({ x: x - 13, y: y - 13, w: 26, h: 26 }))
  const names: Box[] = []
  const districts = map.districts.map((district) => {
    const best = clearest({ kind: 'district', text: district.name, spots: nameSpots(district.label, 4, 112).filter((spot, index) => index === 0 || inside(spot, district.outline)) }, [...badges, ...dots, ...names])
    names.push(best.box)
    return { key: `${district.id}-label`, kind: 'district' as const, text: district.name, ...best.spot, shown: true }
  })
  const wanted = [
    ...pinned.map(({ place, x, y }) => ({ rank: RANK[mainPin(place) as Pin], key: `${place.id}-name`, kind: 'place' as const, text: place.name, spots: placeSpots(x, y) })),
    ...map.water.filter((water) => water.name).map((water) => ({ rank: 3, key: `${water.name}-label`, kind: 'water' as const, text: water.name, spots: nameSpots(water.label, 0, 28) })),
  ]
  // A stable sort keeps the drawing order within a rank, so the same city lays out the same every time.
  const others = wanted.map((item, index) => ({ item, index })).sort((a, b) => a.item.rank - b.item.rank || a.index - b.index).map(({ item }) => {
    const best = clearest(item, [...badges, ...names])
    if (best.hits === 0) names.push(best.box)
    return { key: item.key, kind: item.kind, text: item.text, ...best.spot, shown: best.hits === 0 }
  })
  return [...districts, ...others]
}

/** The first spot clear of everything taken, else the one that covers the least. */
function clearest(item: { kind: MapLabel['kind']; text: string; spots: Spot[] }, taken: Box[]) {
  const width = item.text.length * LETTER[item.kind] + 4
  const found = item.spots.map((spot) => {
    const box = boxOf(spot, width, INK[item.kind])
    return { spot, box, hits: taken.filter((other) => overlaps(box, other)).reduce((sum, other) => sum + (other.weight ?? 10), 0) }
  })
  return found.reduce((most, spot) => spot.hits < most.hits ? spot : most)
}

type Spot = Pick<MapLabel, 'x' | 'y' | 'anchor'>

/** A name's own spot (a neighbourhood's baseline sits 4 below its point), then straight above or below it, a step at a
 * time out to `reach`. */
function nameSpots(at: Point, baseline: number, reach: number): Spot[] {
  const steps = Array.from({ length: reach / 14 }, (_, index) => (index + 1) * 14).flatMap((step) => [-step, step])
  return [0, ...steps].map((dy): Spot => ({ x: at.x, y: at.y + baseline + dy, anchor: 'middle' }))
}

/** Right of the pin, then left, above and below it. */
function placeSpots(x: number, y: number): Spot[] {
  return [{ x: x + 17, y: y + 4, anchor: 'start' }, { x: x - 17, y: y + 4, anchor: 'end' }, { x, y: y - 18, anchor: 'middle' }, { x, y: y + 27, anchor: 'middle' }]
}

function boxOf(spot: Spot, width: number, [above, below]: readonly [number, number]): Box {
  const left = spot.anchor === 'start' ? spot.x : spot.anchor === 'end' ? spot.x - width : spot.x - width / 2
  return { x: left, y: spot.y - above, w: width, h: above + below }
}

function overlaps(a: Box, b: Box): boolean {
  return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h
}

/** Kinds of place drawn as a patch of ground under their pin, like parks on a street map. */
export const GROUNDS: Record<string, string> = { park: 'park', garden: 'park', trail: 'park', beach: 'sand' }
