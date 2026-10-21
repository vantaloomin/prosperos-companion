import assert from 'node:assert/strict'
import test from 'node:test'
import { careersFor, todayIso } from '../../src/features/character/money.ts'
import { completeDefinition } from '../../src/features/character/definition.ts'
import { boughtFor, costsText, goalText, moodOfMoney, paydayText, rentText, workText } from '../../src/features/today/moneyText.ts'
import type { MoneyView } from '../../src/types.ts'

type Budget = Extract<MoneyView, { available: true }>

const budget: Budget = {
  date: '2026-10-05', available: true, currency: { code: 'USD', symbol: '$', name: 'US dollars' }, period: 'month', style: 'balanced',
  career: { id: 'registered-nurse', name: 'Registered nurse', pay: '$$', guessed: true },
  housing: { unit: 'studio', label: 'a studio', neighborhood: 'Towson' },
  budget: { income: 4070, rent: 1280, upkeep: 0, essentials: 1220, fun: 1020, saving: 550 },
  rent_from: 'budget', bought: [],
  payday: { last: '2026-10-02', next: '2026-10-16', cycle_days: 14, today: false },
  left: 200, fun_cycle: 470, tight: false, flush: false, splurge: null, surprise: null, cant_afford: [],
  goal: { label: 'a new laptop', amount: 1500, saved: 900, share: 0.6, custom: false, since: '2026-07-01', stalled: false },
  text: { income: '$4,070', rent: '$1,280', upkeep: '$0', essentials: '$1,220', fun: '$1,020', saving: '$550', left: '$200' },
}

test('money text states payday, mood and goal plainly', () => {
  assert.match(paydayText(budget), /in 11 days\.$/)
  assert.equal(paydayText({ ...budget, payday: { ...budget.payday, next: '2026-10-06' } }), 'Next payday is tomorrow.')
  assert.equal(paydayText({ ...budget, payday: { ...budget.payday, today: true } }), 'Paid today.')
  assert.equal(moodOfMoney({ ...budget, tight: true }, 'Mara'), 'Money is tight for Mara until payday.')
  assert.equal(goalText(budget), 'Saving for a new laptop: 60% there.')
  assert.equal(goalText({ ...budget, goal: { ...budget.goal, stalled: true } }), 'Saving for a new laptop, but nothing is left over to save right now.')
  assert.equal(rentText(budget), 'Rent: about $1,280 a month for a studio in Towson.')
  assert.equal(rentText({ ...budget, rent_from: 'home' }), 'Rent: about $1,280 a month for their home.')
  assert.equal(workText(budget), 'Registered nurse (guessed from who they are), taking home about $4,070 a month.')
})

test('a medieval kingdom has payments on a place and no pension', () => {
  const old = { ...budget, owned: true, retired: true, medieval: true }
  assert.equal(rentText(old), 'Payments: about $1,280 a month for the place they bought.')
  assert.equal(workText(old), 'Given up work, living on what they put by: about $4,070 a month.')
  assert.equal(rentText({ ...old, medieval: false }), 'Mortgage: about $1,280 a month for the place they bought.')
  assert.equal(workText({ ...old, medieval: false }), 'Retired, living on a pension of about $4,070 a month.')
})

test('a currency ending in a full stop never doubles it, and rent names its period (Camelot)', () => {
  const pennies = { ...budget, period: 'week' as const, owned: true, medieval: true, text: { ...budget.text, rent: '9 d.', essentials: '20 d.', fun: '12 d.', saving: '6 d.' } }
  assert.equal(costsText(pennies), 'Everyday costs about 20 d., fun about 12 d., savings about 6 d.')
  assert.equal(rentText(pennies), 'Payments: about 9 d. a week for the place they bought.')
  assert.equal(costsText(budget), 'Everyday costs about $1,220, fun about $1,020, savings about $550.')
})

test('career choices follow the home city era and keep the current pick', () => {
  const careers = [{ id: 'nurse', name: 'Nurse', pay: '$$', eras: ['modern'] }, { id: 'smith', name: 'Smith', pay: '$', eras: ['medieval'] }]
  assert.deepEqual(careersFor(careers, 'medieval', '').map((career) => career.id), ['smith'])
  assert.deepEqual(careersFor(careers, 'medieval', 'nurse').map((career) => career.id), ['nurse', 'smith'])
  assert.equal(careersFor(careers, undefined, '').length, 2)
  assert.equal(todayIso(new Date(2026, 0, 9)), '2026-01-09')
})

test('adult work is listed only with the adult side on, and a current pick always stays', () => {
  const careers = [{ id: 'nurse', name: 'Nurse', pay: '$$', eras: ['modern'] }, { id: 'cam-model', name: 'Webcam model', pay: '$$', eras: ['modern'], adult: true }]
  assert.deepEqual(careersFor(careers, 'modern', '').map((career) => career.id), ['nurse'])
  assert.deepEqual(careersFor(careers, 'modern', '', true).map((career) => career.id), ['nurse', 'cam-model'])
  assert.deepEqual(careersFor(careers, 'modern', 'cam-model').map((career) => career.id), ['nurse', 'cam-model'])
})

test('older saved characters get a default money setup', () => {
  assert.deepEqual(completeDefinition({ name: 'Mira' }).money, { career: '', style: 'balanced', saving_for: '', goal: 0, goal_since: '', employment: '' })
  assert.equal(completeDefinition({ name: 'Mira', money: { career: 'teacher', style: 'careful', saving_for: '', goal: 0, goal_since: '', employment: '' } }).money.career, 'teacher')
})

test('every purchase on the Money panel says where the money went, family costs included', () => {
  assert.equal(boughtFor('family'), 'From their savings')
  assert.equal(boughtFor('owed'), 'Toward what they owe')
  assert.equal(boughtFor('childcare'), 'For the family')
  assert.equal(boughtFor('admin'), 'On errands and paperwork')
  assert.equal(boughtFor(undefined), 'At home')
  assert.equal(boughtFor('something new' as never), 'At home')
})
