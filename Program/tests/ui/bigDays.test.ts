import assert from 'node:assert/strict'
import test from 'node:test'
import { bigDayLine, outingPlace, outingTitle } from '../../src/features/today/outingText.ts'
import { stripAction, stripLine, type WhereState } from '../../src/features/conversation/whereText.ts'

const place = {
  id: 'bal-druid-hill', name: 'Druid Hill Park', kind: 'park', neighborhood: 'Druid Hill', summary: '', cost: '', cuisine: '', city: 'Baltimore',
  big_day: 'b1', title: "Leo's wedding", event: 'wedding', gift: 'a carved jewelry box', standing_up: false,
}
const outing = {
  id: 'o', local_date: '2027-06-12', at_time: '15:00', until_time: '22:00', activity: 'big-day', asked_date: null, place, named: false,
  cost: 0, cost_text: '', state: 'planned' as const, rolls: 0, ended_at: null, undo: false, not_now: false,
}

test('a big day is named by its own title, with your part in it and the gift', () => {
  assert.equal(outingTitle(outing), "Leo's wedding")
  assert.equal(bigDayLine(outing, 'Mira'), "You're Mira's plus-one. They're bringing a carved jewelry box.")
  assert.equal(bigDayLine({ ...outing, state: 'done' }, 'Mira'), "You went as Mira's plus-one. They brought a carved jewelry box.")
  const own = { ...outing, place: { ...place, title: "Mira's wedding", event: 'own_wedding', gift: null, standing_up: true } }
  assert.equal(bigDayLine(own, 'Mira'), "You're in Mira's wedding party.")
  assert.equal(outingPlace(outing), 'Druid Hill Park, Druid Hill')
  assert.equal(outingPlace({ ...outing, place: { ...place, id: '~big-day', name: 'a venue in Chicago', neighborhood: '' } }), 'A venue in Chicago')
  assert.equal(outingPlace({ ...outing, activity: 'dinner' }), 'Park in Druid Hill')
  assert.equal(bigDayLine({ ...outing, activity: 'dinner' }, 'Mira'), '')
})

test('the strip says where the big day is, and it ends with Call it a night', () => {
  const where: WhereState = { state: 'together', kind: 'out', text: '', outing: { ...outing, state: 'now' } }
  const line = stripLine(where, 'Mira')
  assert.equal(line?.lead, "At Leo's wedding at ")
  assert.deepEqual(line?.place, { id: 'bal-druid-hill', name: 'Druid Hill Park' })
  assert.deepEqual(stripAction(where), { action: 'home', label: 'Call it a night' })
  const away = stripLine({ ...where, outing: { ...outing, state: 'now', place: { ...place, id: '~big-day', name: 'a venue in Chicago' } } }, 'Mira')
  assert.equal(away?.lead, "At Leo's wedding at a venue in Chicago")
  assert.equal(stripLine({ ...where, outing: { ...outing, state: 'done' } }, 'Mira')?.lead, "Headed home from Leo's wedding.")
})
