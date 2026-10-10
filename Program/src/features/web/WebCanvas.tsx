import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react'
import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, type Simulation, type SimulationLinkDatum, type SimulationNodeDatum } from 'd3-force'
import { radius, within, type WebData, type WebLink, type WebNode } from './webText'

type Body = SimulationNodeDatum & { id: string }
type Tie = SimulationLinkDatum<Body>
interface Camera { x: number; y: number; k: number }
interface Props { data: WebData; selected: string | null; centre: { id: string; at: number } | null; onSelect: (id: string | null) => void }

const PINNED = 'web-pinned'
const MIN_ZOOM = 0.25
const MAX_ZOOM = 4

/** Where the user dragged people before, so the web keeps their layout (this browser only). */
function readPinned(): Record<string, [number, number]> {
  try { return JSON.parse(localStorage.getItem(PINNED) ?? '{}') as Record<string, [number, number]> } catch { return {} }
}

function savePinned(pinned: Record<string, [number, number]>) {
  try { localStorage.setItem(PINNED, JSON.stringify(pinned)) } catch { /* Storage can be off; the layout still works. */ }
}

/** The web drawn as bubbles and lines that settle with a gentle physics pull, like Obsidian's graph view. */
export function WebCanvas({ data, selected, centre, onSelect }: Props) {
  const svg = useRef<SVGSVGElement>(null)
  const [positions, setPositions] = useState<Positions>({})
  const { bodies, simulation } = useSimulation(data, setPositions)
  const [camera, setCamera] = useState<Camera | null>(null)
  const size = useSize(svg)
  // You start in the middle of the view.
  const view = camera ?? { x: size.width / 2, y: size.height / 2, k: 1 }
  const gestures = useGestures(svg, view, setCamera, bodies, simulation, onSelect)

  // Centre the view on someone picked from the search, the card or the list.
  useEffect(() => {
    const body = centre && bodies.current.get(centre.id)
    if (!body || !size.width) return
    const frame = requestAnimationFrame(() => setCamera((now) => {
      const k = now?.k ?? 1
      return { k, x: size.width / 2 - (body.x ?? 0) * k, y: size.height / 2 - (body.y ?? 0) * k }
    }))
    return () => cancelAnimationFrame(frame)
  }, [centre, size.width, size.height, bodies])

  const near = selected ? within(data, selected, 1) : null
  const at = (id: string) => positions[id] ?? { x: 0, y: 0 }
  return (
    <svg ref={svg} className="web-canvas" role="img" aria-label="Who knows who, as a web. Use the List button for the same people as a list."
      {...gestures.background}>
      <g transform={`translate(${view.x} ${view.y}) scale(${view.k})`}>
        {data.links.map((link) => <WebLine key={`${link.source}|${link.target}`} link={link} a={at(link.source)} b={at(link.target)}
          faded={!!near && link.source !== selected && link.target !== selected} />)}
        {data.nodes.map((node) => <WebBubble key={node.id} node={node} at={at(node.id)} selected={node.id === selected} near={near}
          zoomed={view.k >= 1.4} onGrab={gestures.grab} />)}
      </g>
    </svg>
  )
}

type Positions = Record<string, { x: number; y: number }>

/** Runs the layout for this web, keeping where people already were and where the user pinned them. */
function useSimulation(data: WebData, setPositions: (positions: Positions) => void) {
  const bodies = useRef(new Map<string, Body>())
  const simulation = useRef<Simulation<Body, Tie> | null>(null)
  useEffect(() => {
    const pinned = readPinned()
    const known = bodies.current
    const next = new Map<string, Body>()
    for (const node of data.nodes) {
      const body = known.get(node.id) ?? { id: node.id, ...(pinned[node.id] ? { fx: pinned[node.id][0], fy: pinned[node.id][1] } : {}) }
      if (node.kind === 'you' && body.fx == null) { body.fx = 0; body.fy = 0 }
      next.set(node.id, body)
    }
    bodies.current = next
    const sizes = new Map(data.nodes.map((node) => [node.id, radius(node)]))
    let queued = 0
    const publish = () => {
      queued = 0
      setPositions(Object.fromEntries([...next.values()].map((body) => [body.id, { x: body.x ?? 0, y: body.y ?? 0 }])))
    }
    const sim = forceSimulation([...next.values()])
      .force('link', forceLink<Body, Tie>(data.links.map((link) => ({ source: link.source, target: link.target }))).id((body) => body.id).distance(70).strength(0.6))
      .force('charge', forceManyBody().strength(-160))
      .force('collide', forceCollide<Body>((body) => (sizes.get(body.id) ?? 7) + 6))
      .force('centre', forceCenter(0, 0).strength(0.03))
      .alpha(known.size ? 0.4 : 1)
      .on('tick', () => { if (!queued) queued = requestAnimationFrame(publish) })
    simulation.current = sim
    return () => { sim.stop(); cancelAnimationFrame(queued) }
  }, [data, setPositions])
  return { bodies, simulation }
}

type Point = { x: number; y: number }

function WebLine({ link, a, b, faded }: { link: WebLink; a: Point; b: Point; faded: boolean }) {
  return (
    <line className={`web-link tie-${link.kind}${faded ? ' faded' : ''}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y}><title>{link.label}</title></line>
  )
}

interface BubbleProps { node: WebNode; at: Point; selected: boolean; near: Set<string> | null; zoomed: boolean; onGrab: (event: ReactPointerEvent, id: string) => void }

function WebBubble({ node, at, selected, near, zoomed, onGrab }: BubbleProps) {
  const size = radius(node)
  const named = node.kind === 'you' || node.kind === 'companion' || zoomed || (near?.has(node.id) ?? false)
  const faded = near && !near.has(node.id)
  return (
    <g className={`web-node kind-${node.kind}${selected ? ' selected' : ''}${faded ? ' faded' : ''}`} transform={`translate(${at.x} ${at.y})`}
      onPointerDown={(event) => onGrab(event, node.id)}>
      <circle r={size} />
      <circle className="web-hit" r={Math.max(size, 18)} />
      {named && <text y={size + 13}>{node.name}</text>}
      <title>{node.name}</title>
    </g>
  )
}

function useSize(ref: React.RefObject<SVGSVGElement | null>) {
  const [size, setSize] = useState({ width: 0, height: 0 })
  useEffect(() => {
    const element = ref.current
    if (!element) return
    const observer = new ResizeObserver(([entry]) => setSize({ width: entry.contentRect.width, height: entry.contentRect.height }))
    observer.observe(element)
    return () => observer.disconnect()
  }, [ref])
  return size
}

type Pointer = { x: number; y: number }

/** Drag bubbles, pan the background, zoom with the wheel or two fingers, and tap to pick someone. */
function useGestures(svg: React.RefObject<SVGSVGElement | null>, camera: Camera, setCamera: (next: Camera | null | ((now: Camera | null) => Camera | null)) => void,
  bodies: React.RefObject<Map<string, Body>>, simulation: React.RefObject<Simulation<Body, Tie> | null>, onSelect: (id: string | null) => void) {
  const pointers = useRef(new Map<number, Pointer>())
  const drag = useRef<{ id: string | null; moved: boolean; start: Pointer; camera: Camera; spread: number } | null>(null)
  const local = (event: { clientX: number; clientY: number }): Pointer => {
    const box = svg.current?.getBoundingClientRect()
    return { x: event.clientX - (box?.left ?? 0), y: event.clientY - (box?.top ?? 0) }
  }
  const zoomAt = (point: Pointer, factor: number) => setCamera((now) => {
    const from = now ?? camera
    const k = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, from.k * factor))
    return { k, x: point.x - (point.x - from.x) * (k / from.k), y: point.y - (point.y - from.y) * (k / from.k) }
  })
  const start = (event: ReactPointerEvent, id: string | null) => {
    pointers.current.set(event.pointerId, local(event))
    svg.current?.setPointerCapture(event.pointerId)
    drag.current = { id, moved: false, start: local(event), camera, spread: spread(pointers.current) }
  }
  const grab = (event: ReactPointerEvent, id: string) => { event.stopPropagation(); start(event, id) }
  const move = (event: ReactPointerEvent) => {
    const now = drag.current
    if (!now || !pointers.current.has(event.pointerId)) return
    pointers.current.set(event.pointerId, local(event))
    const point = local(event)
    if (Math.hypot(point.x - now.start.x, point.y - now.start.y) > 4) now.moved = true
    if (pointers.current.size === 2 && now.spread) {
      const centre = midpoint(pointers.current)
      zoomAt(centre, spread(pointers.current) / now.spread)
      now.spread = spread(pointers.current)
      return
    }
    if (now.moved) follow(now, point)
  }
  // A dragged bubble follows the pointer; a dragged background pans the view.
  const follow = (now: NonNullable<typeof drag.current>, point: Pointer) => {
    const body = now.id ? bodies.current.get(now.id) : null
    if (!body) return setCamera({ ...now.camera, x: now.camera.x + point.x - now.start.x, y: now.camera.y + point.y - now.start.y })
    body.fx = (point.x - now.camera.x) / now.camera.k
    body.fy = (point.y - now.camera.y) / now.camera.k
    simulation.current?.alphaTarget(0.2).restart()
  }
  const end = (event: ReactPointerEvent) => {
    pointers.current.delete(event.pointerId)
    const now = drag.current
    if (!now || pointers.current.size) return
    drag.current = null
    simulation.current?.alphaTarget(0)
    if (now.id && now.moved) {
      const body = bodies.current.get(now.id)
      const pinned = readPinned()
      if (body?.fx != null && body.fy != null) savePinned({ ...pinned, [now.id]: [Math.round(body.fx), Math.round(body.fy)] })
    } else if (!now.moved) onSelect(now.id)
  }
  return {
    grab,
    background: {
      onPointerDown: (event: ReactPointerEvent) => start(event, null),
      onPointerMove: move, onPointerUp: end, onPointerCancel: end,
      onWheel: (event: React.WheelEvent) => zoomAt(local(event), event.deltaY < 0 ? 1.15 : 1 / 1.15),
    },
  }
}

function spread(points: Map<number, Pointer>): number {
  const [a, b] = [...points.values()]
  return a && b ? Math.hypot(a.x - b.x, a.y - b.y) : 0
}

function midpoint(points: Map<number, Pointer>): Pointer {
  const [a, b] = [...points.values()]
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }
}
