import { useEffect, useLayoutEffect, useRef, useState, type RefObject } from 'react'

const PAD = 24
const CAPTION = 34
export const ZOOM = { min: 0.2, max: 2.5, step: 1.25 }

const clamp = (value: number) => Math.min(ZOOM.max, Math.max(ZOOM.min, value))

/**
 * Zoom for a drawn map that can show the whole place (the Draft Table's): it opens fitted to its box with a little
 * room round the edge, stays fitted as the box changes size, and fits again whenever `refit` changes (a new place,
 * a part removed, the phone's Map tab opened). +/- buttons, the wheel and a pinch zoom about the middle of the view.
 */
export function useZoom(box: RefObject<HTMLDivElement | null>, map: { width: number; height: number }, on: boolean, refit: string) {
  const [size, setSize] = useState<{ width: number; height: number } | null>(null)
  const [zoom, setZoom] = useState<number | 'fit'>('fit')
  const [fitted, setFitted] = useState(refit)
  if (fitted !== refit) { setFitted(refit); setZoom('fit') }
  const fit = size && size.width > 0 && size.height > 0
    ? Math.min(1, clamp(Math.min((size.width - 2 * PAD) / map.width, (size.height - 2 * PAD) / map.height))) : 1
  const scale = !on ? 1 : zoom === 'fit' ? fit : zoom
  const latest = useRef(scale)
  useEffect(() => { latest.current = scale })

  useEffect(() => {
    const element = box.current
    if (!on || !element || typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(() => setSize({ width: element.clientWidth, height: element.clientHeight - CAPTION }))
    observer.observe(element)
    return () => observer.disconnect()
  }, [box, on])

  // The middle of the view stays where it was as the scale changes.
  const before = useRef(scale)
  useLayoutEffect(() => {
    const element = box.current, ratio = scale / before.current
    before.current = scale
    if (!element || ratio === 1) return
    element.scrollTo((element.scrollLeft + element.clientWidth / 2) * ratio - element.clientWidth / 2,
      (element.scrollTop + element.clientHeight / 2) * ratio - element.clientHeight / 2)
  }, [box, scale])

  // The wheel (and a trackpad's pinch, which arrives as a wheel) zooms; two fingers pinch on a touch screen.
  useEffect(() => {
    const element = box.current
    if (!on || !element) return
    let pinch: { distance: number; scale: number } | null = null
    const apart = (touches: TouchList) => Math.hypot(touches[0].clientX - touches[1].clientX, touches[0].clientY - touches[1].clientY)
    const wheel = (event: WheelEvent) => { event.preventDefault(); setZoom(clamp(latest.current * (event.deltaY < 0 ? 1.1 : 1 / 1.1))) }
    const start = (event: TouchEvent) => { if (event.touches.length === 2) pinch = { distance: apart(event.touches), scale: latest.current } }
    const move = (event: TouchEvent) => {
      if (!pinch || event.touches.length !== 2) return
      event.preventDefault()
      setZoom(clamp(pinch.scale * apart(event.touches) / pinch.distance))
    }
    const end = (event: TouchEvent) => { if (event.touches.length < 2) pinch = null }
    element.addEventListener('wheel', wheel, { passive: false })
    element.addEventListener('touchstart', start, { passive: true })
    element.addEventListener('touchmove', move, { passive: false })
    element.addEventListener('touchend', end)
    return () => {
      element.removeEventListener('wheel', wheel)
      element.removeEventListener('touchstart', start)
      element.removeEventListener('touchmove', move)
      element.removeEventListener('touchend', end)
    }
  }, [box, on])

  return {
    scale, size, fitted: zoom === 'fit',
    zoomIn: () => setZoom(clamp(scale * ZOOM.step)), zoomOut: () => setZoom(clamp(scale / ZOOM.step)), fit: () => setZoom('fit'),
    atMost: scale >= ZOOM.max, atLeast: scale <= ZOOM.min,
  }
}
