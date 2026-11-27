"""The Story's chapters and the time on each line (companion/story_chapters.py): one ongoing story, nothing cleared."""
from datetime import timedelta

from conftest import Chunk
from test_drafting import connect
from test_story import busy_place, ok, say

from companion import story_pursuit


def told(provider, *texts):
    provider.replies = [[Chunk(text), Chunk('', 'stop')] for text in texts]


def later(clock, **gap):
    clock.instant = clock.now() + timedelta(**gap)


def test_every_line_says_its_hour_and_a_story_picked_up_later_is_a_new_chapter(client, clock, provider):
    connect(client)
    told(provider, 'The cafe hums.', 'The barista nods.', 'Morning light.')
    say(client, 'I look around.', 'story-0001')
    later(clock, minutes=50)
    say(client, 'I order a coffee.', 'story-0002')
    opened = ok(client.get('/api/story'))
    # Baltimore's own clock (12:00 UTC is 8:00 AM there), as the scene's time is.
    assert [(line['chapter'], line['local_time']) for line in opened['messages']] == [
        (1, '2026-10-05T08:00'), (1, '2026-10-05T08:00'), (1, '2026-10-05T08:50'), (1, '2026-10-05T08:50')]
    assert opened['chapters'] == [{'number': 1, 'local_time': '2026-10-05T08:00'}] and opened['next_chapter'] is None

    # Left for the night: the next chapter is already waiting when the story is opened, and the next line begins it.
    later(clock, hours=23)
    waiting = ok(client.get('/api/story'))
    assert waiting['next_chapter'] == {'number': 2, 'by': 'time', 'local_time': '2026-10-06T07:50'}
    say(client, 'I come back the next morning.', 'story-0003')
    opened = ok(client.get('/api/story'))
    assert [line['chapter'] for line in opened['messages']] == [1, 1, 1, 1, 2, 2]
    assert opened['chapters'] == [{'number': 1, 'local_time': '2026-10-05T08:00'}, {'number': 2, 'local_time': '2026-10-06T07:50'}]
    assert opened['next_chapter'] is None
    # Chapters are for the page: the narrator still reads the whole story, and is told nothing of them.
    sent = provider.requests[-1]
    assert 'I order a coffee.' in str(sent['messages']) and 'Chapter' not in str(sent['messages']) + sent['system']


def test_a_reply_told_again_much_later_stays_in_its_chapter(client, clock, provider):
    connect(client)
    told(provider, 'The cafe hums.', 'The cafe hums, louder now.')
    say(client, 'I look around.', 'story-0001')
    later(clock, hours=5)
    ok(client.post('/api/story/retry'))
    opened = ok(client.get('/api/story'))
    assert [(line['role'], line['chapter']) for line in opened['messages']] == [('user', 1), ('narrator', 1)]
    assert opened['messages'][1]['local_time'] == '2026-10-05T13:00' and opened['next_chapter'] is None


def test_the_user_can_start_a_chapter_and_take_it_back(client, clock, provider):
    connect(client)
    assert client.post('/api/story/chapter').status_code == 409  # Nothing to follow yet.
    told(provider, 'The cafe hums.', 'A new day.', 'Still here.')
    say(client, 'I look around.', 'story-0001')
    started = ok(client.post('/api/story/chapter'))
    assert started['next_chapter']['number'] == 2 and started['next_chapter']['by'] == 'asked'
    assert len(started['messages']) == 2  # Nothing is cleared.
    assert ok(client.post('/api/story/chapter'))['next_chapter']['number'] == 2  # Asked twice is asked once.
    assert ok(client.delete('/api/story/chapter'))['next_chapter'] is None

    ok(client.post('/api/story/chapter'))
    later(clock, hours=3)  # Asked for and then left a while: one new chapter, not two.
    say(client, 'I stretch.', 'story-0002')
    say(client, 'I sit back down.', 'story-0003')
    opened = ok(client.get('/api/story'))
    assert [line['chapter'] for line in opened['messages']] == [1, 1, 2, 2, 2, 2] and opened['next_chapter'] is None
    # Once something is said in it, it stays.
    assert [line['chapter'] for line in ok(client.delete('/api/story/chapter'))['messages']] == [1, 1, 2, 2, 2, 2]


def test_clearing_the_pages_keeps_the_people_met_and_who_said_yes(client, clock, provider):
    connect(client)
    place, people = busy_place(client, clock)
    ok(client.put('/api/story/scene', json={'city_id': 'baltimore', 'place_id': place['id']}))
    them = people[0]['sheet']
    told(provider, f'"I\'m {them["name"]}," they say.')
    say(client, 'I say hello.', 'story-0001')
    with client.app.state.database.connect(write=True) as connection:
        connection.execute("INSERT INTO dating_swipes (person_key, city_id, town, liked, matched, created_at, source) "
                           "VALUES (?, 'baltimore', '', 1, 1, ?, ?)", (them['key'], client.app.state.database.now(), story_pursuit.SOURCE))
    ok(client.post('/api/story/chapter'))

    cleared = ok(client.delete('/api/story'))
    assert cleared['messages'] == [] and cleared['chapters'] == [] and cleared['next_chapter'] is None
    assert cleared['scene']['place']['id'] == place['id']
    # They are the world's, not the page's: they still know the user, and a yes is still a yes.
    assert [(person['key'], person['matched']) for person in cleared['people']] == [(them['key'], True)]
    told(provider, 'A nod of welcome.')
    say(client, 'I look around.', 'story-0002')
    assert 'The user has met them once and knows their name' in provider.requests[-1]['prompt']
    assert [line['chapter'] for line in ok(client.get('/api/story'))['messages']] == [1, 1]


def test_the_export_is_in_chapters_on_the_citys_clock(client, clock, provider):
    connect(client)
    told(provider, 'The cafe hums.', 'Morning light.')
    say(client, 'I look around.', 'story-0001')
    later(clock, hours=24)
    say(client, 'I come back.', 'story-0002')
    text = ok_text(client.get('/api/export/story', params={'format': 'md'}))
    assert "Times are each city's own." in text
    assert '## Chapter 1 · Monday, October 5, 2026\n\n**You** · 8:00 AM  \n\nI look around.' in text
    assert '## Chapter 2 · Tuesday, October 6, 2026\n\n**You** · 8:00 AM  \n\nI come back.' in text
    assert '<h2>Chapter 2 · Tuesday, October 6, 2026</h2>' in ok_text(client.get('/api/export/story', params={'format': 'html'}))


def ok_text(response):
    assert response.status_code == 200, response.text
    return response.text
