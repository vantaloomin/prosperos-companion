import assert from 'node:assert/strict'
import test from 'node:test'
import { budgetLine, guestCount, planLine, tomorrow } from '../../src/features/character/weddingText.ts'
import { outingTitle } from '../../src/features/today/outingText.ts'
import { stripLine, type WhereState } from '../../src/features/conversation/whereText.ts'

const venue = { id: 'bal-belvedere', name: 'The Belvedere', kind: 'venue', neighborhood: 'Mount Vernon', mapped: true }
const plan = { size: 'proper' as const, size_label: 'A proper wedding', date: '2027-06-12', venue, guest_count: 80 }

test('the wedding plan reads as one plain line', () => {
  assert.match(planLine(plan), /^A proper wedding on .+ at The Belvedere, about 80 guests\.$/)
  assert.match(planLine({ ...plan, size: 'small', size_label: 'Small' }), /^A small wedding on /)
  assert.equal(budgetLine({ budget_text: '$24,000', share_text: '$12,000' }, 'Mira'), "Budget about $24,000; Mira's share, about $12,000, comes from their savings.")
  assert.equal(budgetLine({ budget_text: '', share_text: '' }, 'Mira'), '')
  assert.equal(guestCount({ guest_count: 20, size: 'small' }), 'About 20 guests, close family and a few friends.')
  assert.equal(tomorrow(new Date(2026, 11, 31)), '2027-01-01')
})

test('the wedding day says so on Today and in the strip', () => {
  const place = { id: 'bal-belvedere', name: 'The Belvedere', kind: 'venue', neighborhood: 'Mount Vernon', summary: '', cost: '', cuisine: '', city: 'Baltimore' }
  assert.equal(outingTitle({ activity: 'wedding', place }), 'Your wedding at The Belvedere')
  const outing = { id: 'o', local_date: '2027-06-12', at_time: '15:00', until_time: '23:00', activity: 'wedding', asked_date: null, place, named: false, cost: 0, cost_text: '', state: 'now' as const, rolls: 0, ended_at: null, undo: false, not_now: false }
  const where: WhereState = { state: 'together', kind: 'out', text: '', outing }
  const line = stripLine(where, 'Mira')
  assert.equal(line?.lead, 'Your wedding at ')
  assert.deepEqual(line?.place, { id: 'bal-belvedere', name: 'The Belvedere' })
  const unmapped = stripLine({ ...where, outing: { ...outing, place: { ...place, id: '~venue', name: 'the wedding venue' } } }, 'Mira')
  assert.equal(unmapped?.lead, 'Your wedding at the wedding venue')
  assert.equal(unmapped?.place, null)
  assert.equal(stripLine({ ...where, outing: { ...outing, state: 'done' } }, 'Mira')?.lead, 'Married today at ')
})
