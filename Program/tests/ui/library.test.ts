import assert from 'node:assert/strict'
import { test } from 'node:test'
import { addedText, creditText, downloadedText, highlighted, libraryIntro, librarySummary, shelfName, shownText, type LibraryBook, type OnlineBook } from '../../src/features/character/libraryText.ts'

const book: LibraryBook = { id: 'b', name: 'The Keeper', world: false, source_format: 'EPUB book', source_file: 'keeper.epub', online: '',
  city_id: null, enabled: true, passages: 1432, created_at: '', updated_at: '' }
const wiki: OnlineBook = { key: 'neokosmos', name: 'Neokosmos wiki', city_id: 'grandport', city_name: 'Grandport',
  url: 'https://quietoak.github.io/NeokosmosWiki/', author: 'Oak', licence: 'CC BY-NC-SA 4.0', licence_url: 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
  book_id: null, updated_at: null }

test('a book says whose it is, how big and what it came from', () => {
  assert.equal(librarySummary(book), 'This companion · 1,432 passages · EPUB book')
  assert.equal(librarySummary({ ...book, world: true, passages: 1 }), 'Everyone in this world · 1 passage · EPUB book')
  assert.equal(librarySummary({ ...book, world: true, city_id: 'grandport', source_format: 'TiddlyWiki' }, 'Grandport'),
    'Everyone in Grandport · 1,432 passages · TiddlyWiki')
})

test('the page says whose library it is', () => {
  assert.equal(shelfName(false, 'Mira'), "Mira's library")
  assert.equal(shelfName(true, 'Mira'), "the world's library")
  assert.match(libraryIntro(false, 'Mira'), /^Long texts Mira can draw on: a novel/)
  assert.match(libraryIntro(true), /^Long texts every companion in this world can draw on/)
})

test('adding and downloading say what happened', () => {
  assert.equal(addedText({ name: 'The Keeper', passages: 3 }, "Mira's library"),
    "The Keeper is in Mira's library: 3 passages. The few that fit what you talk about join each reply.")
  assert.equal(downloadedText({ name: 'Neokosmos wiki', passages: 1432, replaced: false }, 'Oak', 'Grandport'),
    "Neokosmos wiki is in this world's library: 1,432 passages from Oak's site. Companions in Grandport draw on it.")
  assert.match(downloadedText({ name: 'Neokosmos wiki', passages: 9, replaced: true }, 'Oak', 'Grandport'), /^Neokosmos wiki is up to date: 9 passages/)
})

test('an online book credits its author and licence', () => {
  assert.equal(creditText(wiki), 'By Oak, shared under CC BY-NC-SA 4.0. Downloaded from quietoak.github.io/NeokosmosWiki.')
})

test('the passage list says how much it shows', () => {
  assert.equal(shownText(20, 1432, false), 'The first 20 of 1,432 passages. Search to find others.')
  assert.equal(shownText(3, 3, false), 'All 3 passages.')
  assert.equal(shownText(0, 3, true), 'No passages match.')
  assert.equal(shownText(1, 3, true), 'The one passage that matches.')
  assert.equal(shownText(2, 3, true), 'The 2 passages that match best.')
})

test('searched words are marked where they start a word', () => {
  assert.deepEqual(highlighted("Edgar's tower and Edgarton", 'edgar'), [["Edgar", true], ["'s tower and ", false], ['Edgar', true], ['ton', false]])
  assert.deepEqual(highlighted('A wedgar', 'edgar'), [['A wedgar', false]])
  assert.deepEqual(highlighted('Plain text', ''), [['Plain text', false]])
})
