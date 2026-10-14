import assert from 'node:assert/strict'
import test from 'node:test'
import { firstName, panelTitle } from '../../src/features/character/panelText.ts'
import { panelHeading } from '../../src/features/character/mediaText.ts'

test('every Character panel heading goes by first name', () => {
  assert.equal(firstName(' Mira  Solano '), 'Mira')
  assert.equal(firstName('Jess'), 'Jess')
  assert.equal(panelTitle('Mira Solano', 'kitchen'), "Mira's kitchen")
  assert.equal(panelTitle('Mira Solano', 'home and belongings'), "Mira's home and belongings")
  assert.equal(panelHeading('Mira Solano'), "Mira's books, shows and music")
})
