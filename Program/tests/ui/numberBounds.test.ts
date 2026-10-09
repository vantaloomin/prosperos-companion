import assert from 'node:assert/strict'
import { test } from 'node:test'
import { bounded } from '../../src/components/numberBounds.ts'

test('a number box never holds more than its most', () => {
  assert.equal(bounded('61478156156', 0, 6), '6')
  assert.equal(bounded('4', 0, 6), '4')
  assert.equal(bounded('1e9', 0, 6), '6')
})

test('the least is enforced only when leaving the box, so 15 can be typed through 1', () => {
  assert.equal(bounded('1', 15, 1440), '1')
  assert.equal(bounded('1', 15, 1440, true), '15')
  assert.equal(bounded('-3', 0, 24, true), '0')
})

test('blank and half-typed values are left alone', () => {
  assert.equal(bounded('', 0, 6, true), '')
  assert.equal(bounded('-', -2, 2), '-')
  assert.equal(bounded('9', undefined, undefined, true), '9')
})
