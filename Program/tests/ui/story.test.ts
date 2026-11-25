import assert from 'node:assert/strict'
import { test } from 'node:test'
import { aroundText, companionLine, openingAction, openingText, personLine, placeGroups, sceneTime, writingText, openingPlace, planText } from '../../src/features/story/storyText.ts'

test('the scene time is the city clock as written', () => {
  assert.equal(sceneTime('2026-10-06T09:05'), 'Tuesday, 9:05 AM')
  assert.equal(sceneTime('2026-10-06T00:30'), 'Tuesday, 12:30 AM')
  assert.equal(sceneTime('2026-10-06T21:40'), 'Tuesday, 9:40 PM')
})

test('who is around reads as a sentence', () => {
  assert.equal(aroundText([]), 'Nobody you would notice is here.')
  assert.equal(aroundText(['the barista']), 'The barista is here.')
  assert.equal(aroundText(['the barista', 'a regular', 'a neighbor']), 'The barista, a regular and a neighbor are here.')
})

test('unnamed people who read the same are counted, not repeated', () => {
  const local = (hood: string) => `a local from ${hood}`
  assert.equal(aroundText(['the barista', local('Little Italy'), local('Little Italy'), local('Harbor East'), local('Little Italy'), local('Fells Point')]),
    'The barista, three locals from Little Italy, a local from Harbor East and a local from Fells Point are here.')
  assert.equal(aroundText([local('Canton'), local('Canton')]), 'Two locals from Canton are here.')
  assert.equal(aroundText(['a neighbor waiting for the bus', 'a neighbor waiting for the bus']), 'Two neighbors waiting for the bus are here.')
  assert.equal(aroundText(['the barista', 'the barista', 'the waitress', 'the waitress']), 'Two baristas and two waitresses are here.')
  assert.equal(aroundText(['Dana, the barista', 'Dana, the barista']), 'Dana, the barista and Dana, the barista are here.')
  // A role of several words takes the plural on its head noun, its last word.
  assert.equal(aroundText(["a head chef at Joe's", "a head chef at Joe's"]), "Two head chefs at Joe's are here.")
  assert.equal(aroundText(['a line cook', 'a line cook', 'a delivery man', 'a delivery man']), 'Two line cooks and two delivery men are here.')
})

test('places are grouped by neighborhood', () => {
  const place = (id: string, neighborhood: string) => ({ id, name: id, kind: 'cafe', neighborhood })
  assert.deepEqual(placeGroups([place('b', 'Canton'), place('a', 'Fells Point'), place('c', 'Canton')]).map(([hood, items]) => [hood, items.map((item) => item.id)]),
    [['Canton', ['b', 'c']], ['Fells Point', ['a']]])
})

test('a person met says how often and where they are now', () => {
  const person = { key: 'k', name: 'Dana Kim', role: 'barista', city: 'Baltimore', meetings: 3, last_met_at: '', notes: [],
    doing: 'working as the barista', place: { id: 'p', name: 'The Daily Grind', city_id: 'baltimore' } }
  assert.equal(personLine(person), 'Met 3 times · now working as the barista at The Daily Grind')
  assert.equal(personLine({ ...person, meetings: 1, doing: 'at home', place: null }), 'Met once · now at home')
  // Someone who said yes when the user asked them out.
  assert.equal(personLine({ ...person, meetings: 1, matched: true, doing: 'at home', place: null }), 'Met once · said yes · now at home')
  assert.equal(personLine({ ...person, doing: 'at their usual spot at The Daily Grind' }), 'Met 3 times · now at their usual spot at The Daily Grind')
})

test('a story not begun says what it is in one line', () => {
  assert.equal(openingText({ city: { name: 'Grandport' } }), 'Your own story in Grandport, told by a narrator.')
})

test('a companion in the scene is named first among who is around', () => {
  assert.equal(aroundText(['Mira']), 'Mira is here.')
  assert.equal(aroundText(['Mira', 'the barista']), 'Mira and the barista are here.')
})

test('the first open names the companion and finds them when the story can go to them', () => {
  const scene = { city: { name: 'Baltimore' } }
  const mira = { key: 'companion:1', id: '1', name: 'Mira', main: true, here: false, doing: 'at work here', city: 'Baltimore',
    place: { id: 'club-charles', name: 'Club Charles', city_id: 'baltimore' }, plan: null }
  assert.equal(openingText(scene), 'Your own story in Baltimore, told by a narrator.')
  assert.deepEqual(openingAction(), { label: 'Look around', line: 'I look around.', find: null })
  assert.equal(openingText(scene, mira), 'Play out a scene with Mira, anywhere in Baltimore.')
  assert.deepEqual(openingAction(mira), { label: 'Find Mira', line: 'I look around for Mira.', find: 'companion:1' })
  // Already where the story is: nowhere to go first.
  assert.deepEqual(openingAction({ ...mira, here: true }), { label: 'Find Mira', line: 'I look around for Mira.', find: null })
  // At home or asleep: the story is still there to play, and the line says why they are not in it.
  const home = { ...mira, place: null, doing: '' }
  assert.equal(openingText(scene, home), "Play out a scene anywhere in Baltimore. Mira isn't out right now.")
  assert.deepEqual(openingAction(home), { label: 'Look around', line: 'I look around.', find: null })
})

test('a plan under way opens as a scene the two are already in', () => {
  const plan = { outing_id: 'o1', companion_id: '1', name: 'Mira', what: 'dinner', until: '21:00', place: 'Lupa', storyline: false, people: [] }
  const mira = { key: 'companion:1', id: '1', name: 'Mira', main: true, here: false, doing: '', city: 'Baltimore',
    place: { id: 'lupa', name: 'Lupa', city_id: 'baltimore' }, plan }
  const scene = { city: { name: 'Baltimore' }, plan: null }
  // The story is somewhere else: the first open offers to go to the plan.
  assert.equal(openingText(scene, mira), 'You and Mira are at Lupa now, for dinner.')
  assert.deepEqual(openingAction(mira), { label: 'Go to Lupa', line: '', find: 'companion:1' })
  assert.equal(companionLine(mira, 'Baltimore'), 'At Lupa for dinner with you')
  // The story is where the plan is: it says so, and starts with the two of them there.
  assert.match(planText(plan), /^Here with Mira for dinner, until 9:00.PM\.$/)
  assert.equal(openingText({ ...scene, plan }, { ...mira, here: true }), '')
  assert.deepEqual(openingAction({ ...mira, here: true }, plan), { label: 'Start the scene', line: '', find: null, begin: true })
  assert.equal(companionLine({ ...mira, here: true }, 'Baltimore'), 'Here with you for dinner')
  // The opening shows under the lines that say who came, until something is said; without a plan, above an empty story.
  const row = (role: 'user' | 'narrator' | 'scene' | 'cast') => ({ role })
  assert.equal(openingPlace({ scene: { plan }, messages: [row('user'), row('narrator'), row('scene'), row('cast')] }), 'bottom')
  assert.equal(openingPlace({ scene: { plan }, messages: [row('scene'), row('cast'), row('user')] }), null)
  assert.equal(openingPlace({ scene: { plan: null }, messages: [row('scene')] }), 'top')
  assert.equal(openingPlace({ scene: { plan: null }, messages: [row('scene'), row('user')] }), null)
})

test('a companion in the people list says where they are now', () => {
  const mira = { key: 'companion:1', id: '1', name: 'Mira', main: true, here: false, doing: '', city: 'Baltimore',
    place: { id: 'club-charles', name: 'Club Charles', city_id: 'baltimore' }, plan: null }
  assert.equal(companionLine({ ...mira, here: true }, 'Baltimore'), 'Here with you')
  assert.equal(companionLine(mira, 'Baltimore'), 'Now at Club Charles')
  assert.equal(companionLine(mira, 'New York'), 'Now at Club Charles, Baltimore')
  assert.equal(companionLine({ ...mira, place: null }, 'Baltimore'), 'Not out right now')
})

test('while a line waits, the narrator writes first and then each companion in the scene answers', () => {
  const row = (id: string, role: 'user' | 'narrator' | 'companion', extra: object = {}) => ({ id, seq: 1, role, text: '', reply_to: null,
    status: 'complete' as const, error: null, city_id: 'b', place_id: 'p', created_at: '', client_id: null, speaker: null, name: null, ...extra })
  const cast = [{ id: '1', name: 'Mira' }]
  assert.equal(writingText([], 'c1', cast), 'The narrator is writing…')
  const sent = row('u1', 'user', { client_id: 'c1' })
  assert.equal(writingText([sent], 'c1', cast), 'The narrator is writing…')
  const told = row('n1', 'narrator', { reply_to: 'u1' })
  assert.equal(writingText([sent, told], 'c1', cast), 'Mira is answering…')
  assert.equal(writingText([sent, told], 'c1', []), 'The narrator is writing…')
  assert.equal(writingText([sent, told, row('m1', 'companion', { reply_to: 'u1', speaker: '1', name: 'Mira' })], 'c1', cast), 'The narrator is writing…')
})
