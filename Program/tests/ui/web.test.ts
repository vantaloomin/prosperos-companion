import assert from 'node:assert/strict'
import { test } from 'node:test'
import { countText, filtered, hoods, search, tiesOf, within, type WebData } from '../../src/features/web/webText.ts'

const data: WebData = {
  nodes: [
    { id: 'you', name: 'Sam', kind: 'you', detail: '', hood: '' },
    { id: 'companion:1', name: 'Mira', kind: 'companion', detail: 'Your companion', hood: '', main: true },
    { id: 'circle:t:0', name: 'Becca Lee', kind: 'circle', detail: 'close friend', hood: '' },
    { id: 'circle:t:0/1', name: 'Jordan Park', kind: 'acquaintance', detail: 'nurse', hood: '' },
    { id: 'town:b:cafe:0', name: 'Dana Cruz', kind: 'townsperson', detail: 'barista at Daily Grind', hood: 'Canton' },
  ],
  links: [
    { source: 'you', target: 'companion:1', label: 'your companion', kind: 'you' },
    { source: 'companion:1', target: 'circle:t:0', label: 'close friend', kind: 'friend' },
    { source: 'circle:t:0/1', target: 'circle:t:0', label: 'coworker', kind: 'work' },
    { source: 'companion:1', target: 'town:b:cafe:0', label: 'met at Daily Grind', kind: 'met' },
  ],
}

test('filters keep you and the links between the people they keep', () => {
  assert.deepEqual(filtered(data, { kind: 'companions' }).nodes.map((node) => node.id), ['you', 'companion:1'])
  assert.equal(filtered(data, { kind: 'companions' }).links.length, 1)
  assert.deepEqual(filtered(data, { kind: 'hood', hood: 'Canton' }).nodes.map((node) => node.id), ['you', 'companion:1', 'town:b:cafe:0'])
  assert.deepEqual([...within(data, 'circle:t:0/1', 2)].sort(), ['circle:t:0', 'circle:t:0/1', 'companion:1'])
  assert.equal(filtered(data, { kind: 'near', id: 'circle:t:0/1' }).nodes.length, 4)
  assert.equal(filtered(data, { kind: 'everyone' }).links.length, 4)
})

test('ties, neighbourhoods, search and counts read plainly', () => {
  assert.deepEqual(tiesOf(data, 'circle:t:0').map((tie) => `${tie.name}: ${tie.label}`), ['Jordan Park: coworker', 'Mira: close friend'])
  assert.deepEqual(hoods(data), ['Canton'])
  assert.deepEqual(search(data, 'da').map((node) => node.name), ['Dana Cruz', 'Jordan Park'])
  assert.deepEqual(search(data, 'a').map((node) => node.name)[0], 'Becca Lee')
  assert.deepEqual(search(data, ' '), [])
  assert.equal(countText(data), '4 people, 4 ties')
})
