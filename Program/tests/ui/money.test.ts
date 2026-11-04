import assert from 'node:assert/strict'
import test from 'node:test'
import { careersFor, guessLabel, payDraft, payPlaceholder, payText, readPay, todayIso, workChoices, workHint } from '../../src/features/character/money.ts'
import { completeDefinition } from '../../src/features/character/definition.ts'
import { boughtFor, costsText, cycleText, goalText, moodOfMoney, ownerText, paydayText, rentText, workText } from '../../src/features/today/moneyText.ts'
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
  assert.equal(moodOfMoney({ ...budget, tight: true }, 'Mara'), 'Money is tight for Mara until payday')
  assert.equal(goalText(budget), 'Saving for a new laptop: 60% there.')
  assert.equal(goalText({ ...budget, goal: { ...budget.goal, stalled: true } }), 'Saving for a new laptop, but nothing is left over to save right now.')
  assert.equal(rentText(budget), 'Rent: about $1,280 a month for a studio in Towson.')
  assert.equal(rentText({ ...budget, rent_from: 'home' }), 'Rent: about $1,280 a month for their home.')
  assert.equal(workText(budget), 'Registered nurse (guessed from who they are), taking home about $4,070 a month.')
})

test('a medieval kingdom has payments on a place and no pension', () => {
  const old = { ...budget, owned: true, retired: true, medieval: true }
  assert.equal(rentText(old), 'Payments: about $1,280 a month for a studio in Towson.')
  assert.equal(workText(old), 'Given up work, living on what they put by: about $4,070 a month.')
  assert.equal(rentText({ ...old, medieval: false }), 'Mortgage: about $1,280 a month for a studio in Towson.')
  assert.equal(workText({ ...old, medieval: false }), 'Retired, living on a pension of about $4,070 a month.')
})

test('a currency ending in a full stop never doubles it, and rent names its period (Camelot)', () => {
  const pennies = { ...budget, period: 'week' as const, owned: true, medieval: true, text: { ...budget.text, rent: '9 d.', essentials: '20 d.', fun: '12 d.', saving: '6 d.' } }
  assert.equal(costsText(pennies), 'Each week: everyday costs about 20 d., fun about 12 d., savings about 6 d.')
  assert.equal(rentText(pennies), 'Payments: about 9 d. a week for a studio in Towson.')
  assert.equal(costsText(budget), 'Each month: everyday costs about $1,220, fun about $1,020, savings about $550.')
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

test('a fantasy city lists its own work, and the guess says what it found', () => {
  const shared = [{ id: 'nurse', name: 'Nurse', pay: '$$', eras: ['modern'] }]
  const ionia = [{ id: 'pit-fighter', name: 'Pit fighter', pay: '$$', eras: ['modern'] }, { id: 'monk', name: 'Monk', pay: '$', eras: ['modern'] }]
  // The shared catalogue has no fantasy careers: only the city's own fill the list.
  assert.deepEqual(careersFor(shared, 'fantasy', ''), [])
  assert.deepEqual(workChoices(ionia, shared, 'fantasy', '').map((career) => career.id), ['monk', 'pit-fighter'])
  assert.deepEqual(workChoices(ionia, shared, 'fantasy', 'nurse').map((career) => career.id), ['monk', 'nurse', 'pit-fighter'])
  assert.deepEqual(workChoices(undefined, shared, 'modern', '').map((career) => career.id), ['nurse'])
  assert.equal(guessLabel(ionia[0]), 'Guess from who they are: Pit fighter ($$)')
  assert.equal(guessLabel(null), 'Guess from who they are: no job named')
  assert.match(workHint(null), /everyday wage\. Pick one to set it\.$/)
  assert.match(workHint(ionia[0]), /^Sets their pay/)
  assert.equal(guessLabel(undefined), 'Guess from who they are')
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

test('the Pay box: empty is worked out, 0 is unpaid, and amounts read with separators', () => {
  assert.equal(readPay(''), null)
  assert.equal(readPay('0'), 0)
  assert.equal(readPay('3,100'), 3100)
  assert.equal(payText(3100), '3,100')
  assert.equal(payText(null), '')
  assert.equal(payDraft('$3,1a00'), '3,100')
  assert.equal(payPlaceholder(2412.4), 'About 2,412 a month from their work')
  assert.equal(payPlaceholder(1_250_000), 'About 1,250,000 a month')
  assert.equal(payPlaceholder(38, true), 'About 38 a month')
})

test('with a pay of their own set, the Work hint says nothing about pay', () => {
  assert.equal(workHint(null, false, true), 'Nothing in “Who they are” names a job. Pick one to set it.')
  assert.equal(workHint(undefined, false, true), 'Sets their hours and kind of work. Their pay is set below.')
  assert.match(workHint(undefined), /^Sets their pay/)
  assert.equal(workHint(undefined, true), 'Hours follow a job it names, such as nurse; otherwise office hours.')
})

test('a home owned outright pays no rent, and owners pay taxes and repairs on top', () => {
  const owner = { ...budget, owned: true, tenure: 'owned' as const, rent_from: 'home' as const, owner_words: 'property tax, insurance and upkeep', text: { ...budget.text, rent: '$0', owner_costs: '$450' } }
  assert.equal(rentText(owner), 'Owns their home outright.')
  assert.equal(ownerText(owner), 'Property tax, insurance and upkeep: about $450 a month.')
  const mortgage = { ...owner, tenure: 'mortgage' as const, text: { ...owner.text, rent: '$1,280' } }
  assert.equal(rentText(mortgage), 'Mortgage: about $1,280 a month for their home.')
  assert.equal(ownerText(mortgage), 'Property tax, insurance and upkeep: about $450 a month.')
  assert.equal(ownerText(budget), null)
})

test('weekly pay is not said twice', () => {
  assert.equal(cycleText({ ...budget, period: 'week' }), '')
  assert.equal(cycleText(budget), 'Paid every other Friday.')
})
