import assert from 'node:assert/strict'
import { test } from 'node:test'
import { currentPermission, mustRevoke, permissionNote } from '../../src/features/notifications/permission.ts'

test('permission reads the browser state', () => {
  assert.equal(currentPermission({ Notification: { permission: 'granted' } }), 'granted')
  assert.equal(currentPermission({}), 'unsupported')
})

test('a withdrawn permission turns notifications off', () => {
  assert.equal(mustRevoke(true, 'denied'), true)
  assert.equal(mustRevoke(true, 'default'), true)
  assert.equal(mustRevoke(true, 'granted'), false)
  assert.equal(mustRevoke(false, 'denied'), false)
})

test('permission notes stay neutral', () => {
  assert.equal(permissionNote('granted'), null)
  assert.match(permissionNote('denied') ?? '', /blocked/)
})
