import assert from 'node:assert/strict'
import test from 'node:test'
import { careersFor, todayIso } from '../../src/features/character/money.ts'
import { completeDefinition } from '../../src/features/character/definition.ts'
import { goalText, moodOfMoney, paydayText, workText } from '../../src/features/today/moneyText.ts'
import type { MoneyView } from '../../src/types.ts'

type Budget = Extract<MoneyView, { available: true }>

const budget: Budget = {
  date: '2026-10-05', available: true, currency: { code: 'USD', symbol: '$', name: 'US dollars' }, period: 'month', style: 'balanced',
  career: { id: 'registered-nurse', name: 'Registered nurse', pay: '$$', guessed: true },
  housing: { unit: 'studio', label: 'a studio', neighborhood: 'Towson' },
  budget: { income: 4070, rent: 1280, essentials: 1220, fun: 1020, saving: 550 },
  payday: { last: '2026-10-02', next: '2026-10-16', cycle_days: 14, today: false },
  left: 200, fun_cycle: 470, tight: false, flush: false, splurge: null, surprise: null, cant_afford: [],
  goal: { label: 'a new laptop', amount: 1500, saved: 900, share: 0.6, custom: false, since: '2026-07-01', stalled: false },
  text: { income: '$4,070', rent: '$1,280', essentials: '$1,220', fun: '$1,020', saving: '$550', left: '$200' },
}

test('money text states payday, mood and goal plainly', () => {
  assert.match(paydayText(budget), /in 11 days\.$/)
  assert.equal(paydayText({ ...budget, payday: { ...budget.payday, next: '2026-10-06' } }), 'Next payday is tomorrow.')
  assert.equal(paydayText({ ...budget, payday: { ...budget.payday, today: true } }), 'Paid today.')
  assert.equal(moodOfMoney({ ...budget, tight: true }, 'Mara'), 'Money is tight for Mara until payday.')
  assert.equal(goalText(budget), 'Saving for a new laptop: 60% there.')
  assert.equal(goalText({ ...budget, goal: { ...budget.goal, stalled: true } }), 'Saving for a new laptop, but nothing is left over to save right now.')
  assert.equal(workText(budget), 'Registered nurse (guessed from who they are), taking home about $4,070 a month.')
})

test('career choices follow the home city era and keep the current pick', () => {
  const careers = [{ id: 'nurse', name: 'Nurse', pay: '$$', eras: ['modern'] }, { id: 'smith', name: 'Smith', pay: '$', eras: ['medieval'] }]
  assert.deepEqual(careersFor(careers, 'medieval', '').map((career) => career.id), ['smith'])
  assert.deepEqual(careersFor(careers, 'medieval', 'nurse').map((career) => career.id), ['nurse', 'smith'])
  assert.equal(careersFor(careers, undefined, '').length, 2)
  assert.equal(todayIso(new Date(2026, 0, 9)), '2026-01-09')
})

test('older saved characters get a default money setup', () => {
  assert.deepEqual(completeDefinition({ name: 'Mira' }).money, { career: '', style: 'balanced', saving_for: '', goal: 0, goal_since: '' })
  assert.equal(completeDefinition({ name: 'Mira', money: { career: 'teacher', style: 'careful', saving_for: '', goal: 0, goal_since: '' } }).money.career, 'teacher')
})
