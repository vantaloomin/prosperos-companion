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
})

test('hidden values read as words, and only when shown', () => {
  assert.equal(numbersLine(view()), null)
  const shown = view({ reader: 3, watcher: 0, library: true, drop: 45, recommend: 40, items: { a: { along: 45, days_left: 1, ends: 'finish' } } })
  assert.equal(numbersLine(shown), "Reads a lot, watches not much, borrows books from the library. Gives up on what they don't like 45% of the time; passes on what they love 40% of the time.")
  assert.equal(itemNumbers(shown, 'a'), '45% through, 1 day to go, will finish it.')
  assert.equal(itemNumbers(shown, 'b'), null)
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
