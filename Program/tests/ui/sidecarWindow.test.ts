import { test } from 'node:test'
import assert from 'node:assert/strict'

// Just enough of a browser for the sidecar store and its window (src/features/sidecar/popout.ts).
const stored = new Map<string, string>()
const storage = { getItem: (key: string) => stored.get(key) ?? null, setItem: (key: string, value: string) => { stored.set(key, value) } }
const element = () => ({ attributes: [], setAttribute() {}, removeAttribute() {}, hasAttribute: () => false })
const page = () => ({
  title: '', body: { replaceChildren() {} }, head: { querySelectorAll: () => [], appendChild() {} },
  documentElement: element(), importNode: (node: unknown) => node, hasFocus: () => true,
})
let blocked = false
let opened = 0
const popup = { document: page(), closed: false, outerWidth: 500, outerHeight: 800, screenX: 1700, screenY: 40, focus() {}, addEventListener() {}, close() { this.closed = true } }
Object.assign(globalThis, {
  localStorage: storage, sessionStorage: { ...storage, getItem: () => null, setItem() {} },
  document: page(), MutationObserver: class { observe() {} disconnect() {} },
  window: { open: () => { if (blocked) return null; opened += 1; popup.closed = false; return popup } },
})

const { sidecar } = await import('../../src/features/sidecar/store.ts')

test('popping out opens its own window and remembers it', () => {
  sidecar.popOut()
  assert.equal(sidecar.get().mode, 'window')
  assert.equal(sidecar.get().open, true)
  assert.equal(stored.get('companion:sidecar-mode'), 'window')
})

test('closing the window closes the sidecar, and it opens there again', () => {
  popup.close()
  sidecar.windowClosed()
  assert.equal(sidecar.get().open, false)
  const before = opened
  sidecar.show()
  assert.equal(opened, before + 1)
  assert.equal(sidecar.get().open, true)
})

test('putting it back docks it and closes the window', () => {
  sidecar.putBack()
  assert.equal(sidecar.get().mode, 'docked')
  assert.equal(sidecar.get().open, true)
  assert.equal(popup.closed, true)
})

test('a blocked window opens docked and says why', () => {
  blocked = true
  sidecar.setOpen(false)
  sidecar.popOut()
  assert.equal(sidecar.get().mode, 'docked')
  assert.equal(sidecar.get().blocked, true)
  assert.equal(stored.get('companion:sidecar-mode'), 'docked')
})
