import assert from 'node:assert/strict'
import { test } from 'node:test'
import { grouped, pieceSince, pieceTitle, wearingText } from '../../src/features/character/wardrobeText.ts'
import type { WardrobeItem } from '../../src/types.ts'

const piece = (extra: Partial<WardrobeItem> = {}): WardrobeItem => ({
  id: 'p', category: 'top', name: 'a cream cable-knit sweater', variety: 'cable-knit sweater', description: '', occasions: 'ch',
  favorite: false, slot: null, origin: 'generated', since: '2026-10-05', until: null, edited: false, revision: 1, ...extra,
})

test('pieces group in the panel order and empty kinds are left out', () => {
  const items = [piece({ id: 'a', category: 'shoes', name: 'white sneakers' }), piece({ id: 'b' }), piece({ id: 'c', category: 'shoes' })]
  assert.deepEqual(grouped(items, ['top', 'bottom', 'shoes']).map(([category, pieces]) => [category, pieces.map((item) => item.id)]),
    [['top', ['b']], ['shoes', ['a', 'c']]])
})

test('titles start with a capital and say where later pieces came from', () => {
  assert.equal(pieceTitle(piece({ name: 'navy scrubs' })), 'Navy scrubs')
  assert.equal(pieceSince(piece()), null)
  assert.equal(pieceSince(piece({ origin: 'user', since: '2026-10-06' })), 'Added by you on 2026-10-06')
  assert.equal(pieceSince(piece({ origin: 'change', since: '2026-10-20' })), 'New since 2026-10-20')
})

test('what they wear now reads as a sentence, and nothing without an outfit', () => {
  assert.equal(wearingText({ label: 'at work', text: 'navy scrubs and nursing clogs' }), 'Wearing right now (at work): navy scrubs and nursing clogs.')
  assert.equal(wearingText(null), null)
  assert.equal(wearingText({ label: 'at home', text: '' }), null)
})
