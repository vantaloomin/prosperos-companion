import assert from 'node:assert/strict'
import { test } from 'node:test'
import { howToUpdate, linkLabel, releasedOn } from '../../src/features/settings/updateText.ts'
import type { UpdateCheck } from '../../src/types.ts'

const found = (change: Partial<UpdateCheck>): UpdateCheck => ({
  status: 'newer', current: '1.1.5', latest: '1.1.6', title: null, published: null,
  page: 'https://github.com/vantaloomin/prosperos-companion/releases/tag/v1.1.6', install: 'folder', system: 'windows', ...change,
})

test('a folder copy is pointed at its own update script', () => {
  assert.match(howToUpdate(found({}), false), /update\.bat in the Windows folder/)
  assert.match(howToUpdate(found({ system: 'mac' }), false), /update\.command in the Mac folder/)
  assert.match(howToUpdate(found({}), false), /^Close the Companion/)
})

test('the installed app is pointed at the new installer, and a phone at the computer', () => {
  assert.match(howToUpdate(found({ install: 'installer' }), false), /^Download the new installer/)
  assert.match(howToUpdate(found({ install: 'installer' }), true), /^Update it on the computer/)
})

test('the release date is left out when GitHub gave none', () => {
  assert.equal(releasedOn(null), '')
  assert.match(releasedOn('2026-10-26T14:58:09Z'), /^, released .*2026/)
})

test('the link says Download only for the installed app on the PC', () => {
  assert.equal(linkLabel(found({ install: 'installer' }), false), 'Download')
  assert.equal(linkLabel(found({ install: 'installer' }), true), 'What’s new')
  assert.equal(linkLabel(found({}), false), 'What’s new')
  assert.equal(linkLabel(found({ status: 'current' }), false), 'What’s new in 1.1.5')
  assert.equal(linkLabel(found({ status: 'unavailable' }), false), 'Releases page')
})
