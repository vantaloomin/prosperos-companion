import assert from 'node:assert/strict'
import { test } from 'node:test'
import { bookSummary, broughtText, entryWhen, momentText, type LoreBook, type LoreEntry } from '../../src/features/character/loreText.ts'

const entry: LoreEntry = { id: 'e', title: 'Brother', text: 'x', keywords: ['Mike', 'brother'], always: false, pattern: false, enabled: true,
  when: [], when_guessed: false, fits_now: false }

test('an imported character says who came and what they brought', () => {
  const text = broughtText({ format: 'Character Card V2', picture: true, stepped_back: 'Mira',
    companion: { version: { name: 'Dana', definition: { identity: 'Works as a nurse. Lives in Fells Point.' } } },
    book: { id: 'b', name: 'Dana lore', world: false, entries: 4, off: 1 } })
  assert.equal(text, 'Dana is here (from a Character Card V2). Works as a nurse. Lives in Fells Point. Their lorebook came too: '
    + '4 lore entries, 1 of them off. Their picture is with their reference pictures. Mira stepped back and keeps everything.')
})

test('a lorebook on its own joins the world', () => {
  assert.equal(broughtText({ format: 'NovelAI lorebook', picture: false, companion: null,
    book: { id: 'b', name: 'Harbor', world: true, entries: 1, off: 0 } }), 'Harbor is now part of this world: 1 lore entry.')
})

test('a picture that was left out says why', () => {
  const text = broughtText({ format: 'Marinara Engine character', picture: false, picture_note: 'Their picture is a WebP image.',
    companion: { version: { name: 'Dana', definition: { identity: '' } } }, book: null })
  assert.equal(text, 'Dana is here (from a Marinara Engine character). Their picture is a WebP image.')
})

test('entries say when they come up', () => {
  assert.equal(entryWhen(entry), 'When someone mentions Mike, brother')
  assert.equal(entryWhen({ ...entry, always: true }), 'Always')
  assert.match(entryWhen({ ...entry, pattern: true }), /stays off/)
})

test('a book says whose it is and how much is on', () => {
  const book: LoreBook = { id: 'b', name: 'B', description: '', source_format: 'SillyTavern world info', source_file: 'b.json',
    world: true, enabled: true, city: false, created_at: '', entries: [entry, { ...entry, enabled: false }] }
  assert.equal(bookSummary(book), 'Everyone in this world · 1 of 2 entries on · SillyTavern world info')
  assert.equal(bookSummary({ ...book, city: true }), 'Comes with the city · 1 of 2 entries on')
})

test('an entry that fits the moment says when, in words', () => {
  const rain = { key: 'weather:rain', label: 'Rain' }
  const snow = { key: 'weather:snow', label: 'Snow' }
  const night = { key: 'time:night', label: 'Night' }
  assert.equal(momentText([rain, snow, night]), 'on rainy days or on snowy days, at night')
  assert.equal(momentText([{ key: 'holiday:Christmas Day', label: 'Christmas Day' }, { key: 'place:hampden', label: 'Hampden' }]),
    'on Christmas Day, in Hampden')
  assert.equal(momentText([{ key: 'season:fall', label: 'Fall' }, { key: 'work:yes', label: 'At work' }]), 'in fall, at work')
  assert.equal(entryWhen({ ...entry, keywords: [], when: [rain, night] }), 'On rainy days, at night')
  assert.equal(entryWhen({ ...entry, when: [night] }), 'When someone mentions Mike, brother. Also at night')
  assert.equal(entryWhen({ ...entry, keywords: [], when: [] }), 'Never: it has no words or moment')
})
