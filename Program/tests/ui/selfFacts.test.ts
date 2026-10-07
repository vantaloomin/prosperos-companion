import assert from 'node:assert/strict'
import { test } from 'node:test'
import { conflictText, orderFacts, selfFactText } from '../../src/features/character/selfFactText.ts'
import type { SelfFact } from '../../src/types.ts'

const fact = (category: SelfFact['category'], subject: string, value: string, status: SelfFact['status'] = 'noted'): SelfFact => ({
  id: `${category}:${subject}`, message_id: 'm', category, label: category === 'dislikes' ? 'Dislikes' : category, subject, value,
  statement: '', status, conflicts_with: null, created_at: '', decided_at: null,
})

test('facts read as short lines', () => {
  assert.equal(selfFactText(fact('person', 'brother', 'Theo')), 'Their brother is named Theo')
  assert.equal(selfFactText(fact('favorite', 'band', 'The National')), 'Favorite band: The National')
  assert.equal(selfFactText(fact('never', 'been to europe', 'Europe')), 'Has never been to europe')
  assert.equal(selfFactText(fact('dislikes', 'cilantro', 'cilantro')), 'Dislikes: cilantro')
})

test('conflicts come first', () => {
  const list = orderFacts([fact('likes', 'jazz', 'jazz'), fact('likes', 'cilantro', 'cilantro', 'conflict')])
  assert.deepEqual(list.map((item) => item.subject), ['cilantro', 'jazz'])
})

test('a conflict says what it is with', () => {
  const waiting = fact('person', 'sister', 'Jo', 'conflict')
  assert.equal(conflictText({ ...waiting, user_said: 'Your sister is Ashley, not Jo.' }), 'you said: “Your sister is Ashley, not Jo.”')
  assert.equal(conflictText({ ...waiting, user_said: '' }), 'you said this was wrong')
  assert.equal(conflictText({ ...waiting, definition_says: 'Mercy Hospital' }), 'their character says Mercy Hospital')
  assert.equal(conflictText({ ...waiting, circle_person: 'sister Ashley' }), 'their circle has sister Ashley')
  assert.equal(conflictText(waiting), 'contradicts something they said earlier')
})
