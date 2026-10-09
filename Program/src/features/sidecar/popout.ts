/**
 * The sidecar in its own browser window (Iris's sidecar-pop-out.md): an empty same-origin pop-up the main app
 * renders the sidecar into with a portal (SidecarWindow), so it shares the main window's React tree and sidecar
 * store and needs no syncing. The window belongs to the main tab and closes with it; the sidecar's conversation is
 * not kept across reloads anyway.
 */
const NAME = 'companion-sidecar'
const PLACE_KEY = 'companion:sidecar-window'
const TITLE = "Sidecar · Prospero's Companion"

let popup: Window | null = null

interface Place { width: number; height: number; left?: number; top?: number }

function readPlace(): Place {
  try {
    const saved = JSON.parse(localStorage.getItem(PLACE_KEY) ?? 'null') as Place | null
    if (saved && saved.width > 200 && saved.height > 200) return saved
  } catch { /* The first size. */ }
  return { width: 420, height: 720 }
}

/** Where the window is now, so it reopens there (a second monitor included). */
export function rememberPlace() {
  if (!popup || popup.closed) return
  const place: Place = { width: popup.outerWidth, height: popup.outerHeight, left: popup.screenX, top: popup.screenY }
  try { localStorage.setItem(PLACE_KEY, JSON.stringify(place)) } catch { /* It opens at the default size. */ }
}

/** The open window, if there is one. */
export function current(): Window | null {
  return popup && !popup.closed ? popup : null
}

/** Opens (or focuses) the window; null when the browser blocked it. Call it from a click or key press. */
export function openWindow(): Window | null {
  if (current()) { popup!.focus(); return popup }
  const place = readPlace()
  const features = [`popup`, `width=${place.width}`, `height=${place.height}`,
    ...(place.left !== undefined ? [`left=${place.left}`, `top=${place.top}`] : [])].join(',')
  const opened = window.open('', NAME, features)
  if (!opened) return null
  popup = opened
  prepare(opened)
  return opened
}

export function closeWindow() {
  rememberPlace()
  current()?.close()
  popup = null
}

export function setWindowTitle(waiting: boolean) {
  const found = current()
  if (found) found.document.title = `${waiting ? '(1) ' : ''}${TITLE}`
}

/** An empty page with the app's styles and theme, kept in step with the main window's. */
function prepare(target: Window) {
  const doc = target.document
  doc.title = TITLE
  doc.body.replaceChildren()
  doc.head.querySelectorAll('link[rel="stylesheet"], style').forEach((node) => node.remove())
  copyStyles(doc)
  copyRoot(doc)
  const styles = new MutationObserver(() => copyStyles(doc))
  styles.observe(document.head, { childList: true, subtree: true, characterData: true })
  const root = new MutationObserver(() => copyRoot(doc))
  root.observe(document.documentElement, { attributes: true })
  target.addEventListener('pagehide', () => { styles.disconnect(); root.disconnect() })
}

function copyStyles(doc: Document) {
  const marked = (node: Element) => node.getAttribute('data-copied') === 'yes'
  doc.head.querySelectorAll('[data-copied]').forEach((node) => { if (marked(node)) node.remove() })
  document.head.querySelectorAll('link[rel="stylesheet"], style').forEach((node) => {
    const copy = doc.importNode(node, true) as Element
    // An empty pop-up's own address is about:blank, so links point at the main window's.
    if (node instanceof HTMLLinkElement) copy.setAttribute('href', node.href)
    copy.setAttribute('data-copied', 'yes')
    doc.head.appendChild(copy)
  })
}

function copyRoot(doc: Document) {
  const from = document.documentElement
  const to = doc.documentElement
  for (const { name, value } of Array.from(from.attributes)) to.setAttribute(name, value)
  for (const { name } of Array.from(to.attributes)) if (!from.hasAttribute(name)) to.removeAttribute(name)
}
