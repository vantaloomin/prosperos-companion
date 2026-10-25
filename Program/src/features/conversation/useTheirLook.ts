import { useEffect, useMemo, useState, type CSSProperties, type RefObject } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api'
import { groundOf, lookStyles, THEIR_LOOK_KEY, type LookView, type TheirLook } from './theirLook'

/** The open companion's look and the Character page's "Their look" (companion/their_look.py). */
export function useTheirLook() {
  return useQuery({ queryKey: THEIR_LOOK_KEY, queryFn: () => api<LookView>('/their-look') })
}

/** Group chat members' looks by companion id, in join order (who joined first keeps theirs). */
export function useGroupLooks(ids: string[]) {
  const joined = ids.join(',')
  return useQuery({ queryKey: [...THEIR_LOOK_KEY, 'group', joined], enabled: ids.length > 0,
    queryFn: () => api<{ looks: Record<string, TheirLook | null> }>(`/their-look/group?ids=${encodeURIComponent(joined)}`) })
}

const LIGHT_QUERY = '(prefers-color-scheme: light)'

/** Each look's CSS variables, worked out against the chat element's own colours, and again whenever the app's colours
 * (the page root), the computer's light or dark, or the chat's style change. */
export function useLookStyles(element: RefObject<HTMLElement | null>, looks: Record<string, TheirLook | null | undefined>) {
  const [styles, setStyles] = useState<Record<string, CSSProperties>>({})
  const wanted = JSON.stringify(looks)
  const parsed = useMemo(() => JSON.parse(wanted) as Record<string, TheirLook | null>, [wanted])
  useEffect(() => {
    const work = () => {
      const ground = element.current ? groundOf(element.current) : null
      const found: Record<string, CSSProperties> = {}
      for (const [key, look] of Object.entries(parsed)) if (look && ground) found[key] = lookStyles(look, ground) as CSSProperties
      setStyles((current) => JSON.stringify(current) === JSON.stringify(found) ? current : found)
    }
    work()
    const observer = new MutationObserver(work)
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'style'] })
    if (element.current) observer.observe(element.current, { attributes: true, attributeFilter: ['class'] })
    const query = window.matchMedia(LIGHT_QUERY)
    query.addEventListener('change', work)
    return () => { observer.disconnect(); query.removeEventListener('change', work) }
  }, [element, parsed])
  return styles
}

/** The open chat's look: the section's class, style and font, and the lines where the app changed it. */
export function useChatLook(section: RefObject<HTMLElement | null>) {
  const view = useTheirLook().data
  const look = view?.look ?? null
  const style = useLookStyles(section, { theirs: look }).theirs
  if (!style || !look || !view) return { className: '', style: undefined, font: undefined, changes: [] }
  return { className: ' their-look', style, font: look.font, changes: view.changes }
}

/** A group chat's members' name styles, read by companion id; guests and the user have none. */
export function useGroupLookStyles(section: RefObject<HTMLElement | null>, members: { companion_id: string | null }[]) {
  const ids = members.flatMap((member) => member.companion_id ? [member.companion_id] : [])
  const styles = useLookStyles(section, useGroupLooks(ids).data?.looks ?? {})
  return (companionId: string | null) => companionId ? styles[companionId] : undefined
}
