import assert from 'node:assert/strict'
import test from 'node:test'
import { MEDIA_LEVELS, itemNumbers, kindLabel, kindNoun, numbersLine } from '../../src/features/character/mediaText.ts'
import { boughtFor } from '../../src/features/today/moneyText.ts'
import type { MediaView } from '../../src/types.ts'

const view = (numbers?: MediaView['numbers']): MediaView => ({ off: false, today: '2026-10-05', realism: 2, real: true, now: [], lately: [], numbers })

test('each kind has its own label and the slider four steps', () => {
  assert.deepEqual(['book', 'show', 'music'].map((kind) => kindLabel(kind as 'book')), ['Reading', 'Watching', 'On repeat'])
  assert.equal(kindNoun('music'), 'song')
  assert.equal(MEDIA_LEVELS.length, 4)
  assert.equal(boughtFor('media'), 'For their downtime')
  assert.equal(boughtFor('wedding'), 'From their savings')
})

test('hidden values read as words, and only when shown', () => {
  assert.equal(numbersLine(view()), null)
  const shown = view({ reader: 3, watcher: 0, library: true, drop: 45, recommend: 40, items: { a: { along: 45, days_left: 1, ends: 'finish' } } })
  assert.equal(numbersLine(shown), "Reads a lot, watches not much, borrows books from the library. Gives up on what they don't like 45% of the time; tells you about something they loved 40% of the time.")
  assert.equal(itemNumbers(shown, 'a'), '45% through, 1 day to go, will finish it.')
  assert.equal(itemNumbers(shown, 'b'), null)
  assert.equal(itemNumbers(shown, 'a', 'music'), 'On repeat for 1 more day.')
})

test('the heading goes by first name and titles and verdicts split out of the line', async () => {
  const { panelHeading, titled, verdictSplit, byLabel } = await import('../../src/features/character/mediaText.ts')
  assert.equal(panelHeading('Dana Reyes'), "Dana's books, shows and music")
  assert.equal(panelHeading('Jess'), "Jess's books, shows and music")
  assert.deepEqual(titled('Reading Ripley by X: about halfway.', 'Ripley'), ['Reading ', ' by X: about halfway.'])
  assert.equal(titled('Reading A', 'B'), null)
  assert.deepEqual(verdictSplit('Finished Ripley: loved it.'), ['Finished Ripley', 'loved it'])
  assert.deepEqual(verdictSplit('Gave up on Ripley partway through.'), ['Gave up on Ripley partway through.', null])
  assert.equal(byLabel('show'), null)
})

test('change-form examples come from their own time and place, and a recommendation says what waits', async () => {
  const { examples, recommendedNote } = await import('../../src/features/character/mediaText.ts')
  assert.equal(examples('book').title, 'e.g. Piranesi')
  assert.deepEqual(examples('music', 'jazz-age'), { title: 'e.g. Sweet Georgia Brown', by: 'e.g. Ben Bernie' })
  assert.equal(examples('show', 'tales').title, 'e.g. The Trial of the Talking Pig')
  assert.deepEqual(examples('book', 'future'), { title: '', by: '' })
  const item = { id: 'r', kind: 'book' as const, title: 'The Great Gatsby', by: '', format: 'book', text: '', set_by_you: false, started_on: '', recommended: true }
  assert.equal(recommendedNote({ ...item, waiting: 'In Our Time' }), 'You recommended it. In Our Time waits until they finish.')
  assert.equal(recommendedNote(item), 'You recommended it.')
})
