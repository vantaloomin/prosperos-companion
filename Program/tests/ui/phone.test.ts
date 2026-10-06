import assert from 'node:assert/strict'
import { test } from 'node:test'
import { codeFromAddress, guessDeviceName, keyBytes, linkParts, pushHint } from '../../src/features/phone/pairing.ts'
import { availableTabs, pickTab, searchSettings } from '../../src/features/settings/sections.ts'

test('the pairing link carries the code', () => {
  assert.equal(codeFromAddress('?pair=ABCD-EFGH'), 'ABCD-EFGH')
  assert.equal(codeFromAddress(''), '')
})

test('a phone gets a sensible starting name', () => {
  assert.equal(guessDeviceName('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)'), 'iPhone')
  assert.equal(guessDeviceName('Mozilla/5.0 (Linux; Android 15; Pixel 9) Mobile Safari'), 'Android phone')
  assert.equal(guessDeviceName('Mozilla/5.0 (X11; Linux x86_64)'), 'Phone')
})

test('a Tailscale link in an error can be opened', () => {
  const parts = linkParts('Open https://login.tailscale.com/f/serve?node=abc, allow it, then try again.')
  assert.deepEqual(parts.filter((part) => part.link).map((part) => part.text), ['https://login.tailscale.com/f/serve?node=abc'])
  assert.equal(parts.map((part) => part.text).join(''), 'Open https://login.tailscale.com/f/serve?node=abc, allow it, then try again.')
})

test('Phone access has a tab, and Backups stays off a phone', () => {
  assert.ok(availableTabs(true).some((tab) => tab.id === 'phone'))
  assert.ok(!availableTabs(true, true).some((tab) => tab.id === 'data'))
  assert.equal(pickTab('data', true, true), 'general')
  assert.deepEqual(searchSettings('tailscale', true).map((match) => match.section.heading), ['phone-heading'])
  assert.deepEqual(searchSettings('restore', true, true), [])
})

test('the push key turns into the bytes the browser wants', () => {
  assert.deepEqual([...keyBytes('AQID_w')], [1, 2, 3, 255])
})

test('iPhones are told to install first before push works', () => {
  assert.equal(pushHint(true, 'iPhone'), null)
  assert.match(pushHint(false, 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)') ?? '', /home screen/)
  assert.match(pushHint(false, 'Firefox') ?? '', /cannot/)
})
