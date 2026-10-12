"""Exporting a chat or the story as HTML or Markdown, built from the stored messages (companion/export.py)."""
import base64
from datetime import timedelta

import pytest
from test_groups import companion_named
from test_pictures import png

from companion import export, groups, pictures, story
from companion.clock import stamp
from companion.database import identifier
from companion.images import storage


def ok(response):
    assert response.status_code == 200, response.text
    return response


@pytest.fixture
def chat(client, companion, clock):
    """Mira's chat, with the user in New York: the chat's times are the user's own."""
    ok(client.put('/api/settings', json={'user_timezone': 'America/New_York'}))
    return {'timeline': companion['active_timeline_id'], 'version': companion['active_version_id'], 'seq': 0}


def add(client, chat, role, text, at, **extra) -> str:
    """A stored message `at` minutes after the test's start (12:00 UTC, 8:00 AM in New York)."""
    database = client.app.state.database
    chat['seq'] += 1
    message_id = extra.pop('id', identifier())
    row = {'status': 'complete', 'active': 1, 'reply_to': None} | extra
    created = stamp(database.clock.now() + timedelta(minutes=at))
    with database.connect(write=True) as connection:
        connection.execute(
            'INSERT INTO messages (id, timeline_id, seq, role, text, reply_to, status, active, character_version_id, '
            'redacted_at, superseded_at, held_until, created_at, completed_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (message_id, chat['timeline'], chat['seq'], role, text, row['reply_to'], row['status'], row['active'],
             chat['version'], row.get('redacted_at'), row.get('superseded_at'), row.get('held_until'), created,
             created))
    return message_id


def exported(client, path, kind='html'):
    return ok(client.get(f'/api/export/{path}', params={'format': kind}))


def test_html_escapes_every_message_and_loads_nothing(client, chat):
    asked = add(client, chat, 'user', '<script>alert("hi")</script> & you?', 0)
    add(client, chat, 'companion', 'Fine <img src=x onerror=alert(1)>\n\nNew paragraph.', 1, reply_to=asked)
    response = exported(client, f"chat/{chat['timeline']}")
    page = response.text
    assert response.headers['content-type'].startswith('text/html')
    assert response.headers['content-disposition'] == (
        'attachment; filename="Mira - chat - 2026-10-05.html"; filename*=UTF-8\'\'Mira%20-%20chat%20-%202026-10-05.html')
    assert '<script>' not in page and '<img src=x' not in page
    assert '&lt;script&gt;alert(&quot;hi&quot;)&lt;/script&gt; &amp; you?' in page
    assert 'Fine &lt;img src=x onerror=alert(1)&gt;</p><p>New paragraph.</p>' in page
    # One file: inline CSS, nothing fetched from anywhere.
    assert "default-src 'none'; img-src data:" in page and '<style>' in page
    assert 'http://' not in page and 'https://' not in page
    assert '<h1>Mira</h1>' in page


def test_times_are_the_users_own_and_days_are_headed(client, chat):
    add(client, chat, 'user', 'Morning!', 0)
    add(client, chat, 'companion', 'Evening the next day.', 60 * 24 + 600)
    page = exported(client, f"chat/{chat['timeline']}").text
    assert 'Times are in America/New_York.' in page
    assert 'Chat · October 5, 2026 – October 6, 2026' in page
    assert '<h2>Monday, October 5, 2026</h2>' in page and '<h2>Tuesday, October 6, 2026</h2>' in page
    assert '<strong>You</strong> <time datetime="2026-10-05T08:00-04:00">8:00 AM</time>' in page
    assert '<strong>Mira</strong> <time datetime="2026-10-06T18:00-04:00">6:00 PM</time>' in page


def test_only_what_the_chat_shows_is_exported(client, chat, clock):
    asked = add(client, chat, 'user', 'Shown question', 0)
    add(client, chat, 'companion', 'An earlier alternative', 1, reply_to=asked, active=0)
    add(client, chat, 'companion', 'A failed attempt', 2, reply_to=asked, active=0, status='failed')
    add(client, chat, 'companion', 'A withheld reply', 2, reply_to=asked, active=0, status='withheld')
    add(client, chat, 'companion', 'The chosen reply', 3, reply_to=asked)
    add(client, chat, 'user', 'A deleted message', 4, redacted_at=stamp(clock.now()))
    add(client, chat, 'companion', 'Replaced by an edit', 5, superseded_at=stamp(clock.now()))
    add(client, chat, 'companion', 'Held until later', 6, held_until=stamp(clock.now() + timedelta(hours=2)))
    for kind in ('html', 'md'):
        text = exported(client, f"chat/{chat['timeline']}", kind).text
        assert 'Shown question' in text and 'The chosen reply' in text
        for hidden in ('earlier alternative', 'failed attempt', 'withheld reply', 'deleted message', 'Replaced by',
                       'Held until'):
            assert hidden not in text


def test_markdown_is_plain_text_that_stays_text(client, chat):
    asked = add(client, chat, 'user', '# not a heading\n<b>bold?</b>\n- not a list', 0)
    add(client, chat, 'companion', 'Two lines\nof *reply*.', 1, reply_to=asked)
    response = exported(client, f"chat/{chat['timeline']}", 'md')
    text = response.text
    assert response.headers['content-type'].startswith('text/markdown')
    assert 'filename="Mira - chat - 2026-10-05.md"' in response.headers['content-disposition']
    assert text.startswith('# Mira\n\nChat · October 5, 2026  \nTimes are in America/New_York.')
    assert '## Monday, October 5, 2026' in text
    assert '**You** · 8:00 AM  \n\n\\# not a heading  \n&lt;b>bold?&lt;/b>  \n\\- not a list' in text
    assert '**Mira** · 8:01 AM  \n\nTwo lines  \nof *reply*.' in text
    assert '<b>' not in text


def test_pictures_are_embedded_in_html_and_described_in_markdown(client, chat):
    database = client.app.state.database
    sent, made = png(4, 3), png(6, 5)
    picture = pictures.save(database, sent)
    asked = add(client, chat, 'user', 'Look at this', 0)
    reply = add(client, chat, 'companion', 'Here is mine', 1, reply_to=asked)
    with database.connect(write=True) as connection:
        pictures.attach(connection, asked, [picture['id']])
        connection.execute("UPDATE message_pictures SET status='seen', description=? WHERE id=?",
                           ('A dog <asleep> on a sofa', picture['id']))
        chat_photo(connection, database, chat, reply, made)
    page = exported(client, f"chat/{chat['timeline']}").text
    assert f'src="data:image/png;base64,{base64.b64encode(sent).decode()}"' in page
    assert f'src="data:image/png;base64,{base64.b64encode(made).decode()}"' in page
    assert '<figcaption>A dog &lt;asleep&gt; on a sofa</figcaption>' in page
    assert '<figcaption>Mira at the pier</figcaption>' in page
    text = exported(client, f"chat/{chat['timeline']}", 'md').text
    assert '*[Picture: A dog &lt;asleep> on a sofa]*' in text and '*[Picture: Mira at the pier]*' in text
    assert 'the HTML export keeps the pictures themselves' in text
    assert 'base64' not in text


def chat_photo(connection, database, chat, message_id, data):
    """A finished photo Mira sent with her reply, as the image runner leaves one."""
    post_id, job_id, now = identifier(), identifier(), database.now()
    connection.execute("INSERT INTO feed_posts (id, timeline_id, kind, idempotency_key, occurs_at, created_at) "
                       "VALUES (?, ?, 'event', ?, ?, ?)", (post_id, chat['timeline'], post_id, now, now))
    stored = storage.store(database, job_id, data)
    connection.execute(
        'INSERT INTO image_jobs (id, post_id, timeline_id, status, trigger, inputs, character_version_id, '
        "classification, classifier, routing_reason, output_file, created_at) VALUES (?, ?, ?, 'completed', "
        "'automatic', '{}', ?, 'safe', 'test', 'test', ?, ?)",
        (job_id, post_id, chat['timeline'], chat['version'], stored['file'], now))
    connection.execute('INSERT INTO chat_photos (message_id, post_id, job_id, summary, created_at) '
                       'VALUES (?, ?, ?, ?, ?)', (message_id, post_id, job_id, 'Mira at the pier', now))


def test_a_missing_picture_file_is_noted_not_fatal(client, chat):
    database = client.app.state.database
    picture = pictures.save(database, png())
    asked = add(client, chat, 'user', 'Look', 0)
    with database.connect(write=True) as connection:
        pictures.attach(connection, asked, [picture['id']])
    (pictures.folder(database) / f"{picture['id']}.png").unlink()
    assert '[A picture that is no longer in the app]' in exported(client, f"chat/{chat['timeline']}").text


def test_voice_notes_are_exported_as_their_transcript(client, chat):
    note = add(client, chat, 'companion', 'Just wanted to hear your voice.', 0)
    database = client.app.state.database
    with database.connect(write=True) as connection:
        connection.execute("INSERT INTO voice_notes (message_id, file, media_type, duration_ms, engine, voice, "
                           "created_at) VALUES (?, 'n.wav', 'audio/wav', 2000, 'builtin', 'v', ?)",
                           (note, database.now()))
    page = exported(client, f"chat/{chat['timeline']}").text
    assert '<span class="tag">· voice note</span></p><p>Just wanted to hear your voice.</p>' in page
    assert '**Mira** · 8:00 AM · voice note' in exported(client, f"chat/{chat['timeline']}", 'md').text


def test_a_group_chat_names_each_speaker(client, companion, chat):
    billy = companion_named(client, 'Billy Hart')
    group_id = ok(client.post('/api/groups', json={'companion_ids': [companion['id'], billy],
                                                   'name': 'Pier <crew>'})).json()['id']
    database = client.app.state.database
    with database.connect(write=True) as connection:
        groups.add_line(connection, group_id, database.now(), 'user', '', 'Hi both')
        groups.add_line(connection, group_id, database.now(), groups.member_key(billy), 'Billy', 'Hey <you>')
        groups.add_line(connection, group_id, database.now(), groups.member_key(billy), 'Billy', 'Half-written',
                        status='failed')
    response = exported(client, f'chat/{group_id}')
    page = response.text
    assert 'filename="Pier crew - group chat - 2026-10-05.html"' in response.headers['content-disposition']
    assert '<h1>Pier &lt;crew&gt;</h1>' in page and 'Group chat · October 5, 2026' in page
    assert '<p class="note">You started a group with Mira and Billy. <time>8:00 AM</time></p>' in page
    assert '<strong>You</strong>' in page and '<p>Hi both</p>' in page
    assert '<strong>Billy</strong>' in page and 'Hey &lt;you&gt;' in page
    assert 'Half-written' not in page
    text = exported(client, f'chat/{group_id}', 'md').text
    assert '**Billy** · 8:00 AM  \n\nHey &lt;you>' in text


def test_the_story_exports_with_its_narrator_and_places(client, chat):
    assert client.get('/api/export/story').status_code == 404  # Story mode is off.
    ok(client.put('/api/settings', json={'story_mode': True}))
    database = client.app.state.database
    where = {'city_id': 'baltimore', 'place_id': 'somewhere'}
    with database.connect(write=True) as connection:
        story.add(connection, database.now(), 'scene', 'You arrive at the cafe.', where)
        story.add(connection, database.now(), 'user', 'I order a coffee.', where)
        story.add(connection, database.now(), 'narrator', 'The barista nods.', where)
        story.add(connection, database.now(), 'narrator', 'Lost words', where, status='failed')
    response = exported(client, 'story', 'md')
    text = response.text
    assert 'filename="Story - 2026-10-05.md"' in response.headers['content-disposition']
    assert text.startswith('# Story\n\nStory in Baltimore · October 5, 2026')
    assert '*You arrive at the cafe. (8:00 AM)*' in text
    assert '**You** · 8:00 AM  \n\nI order a coffee.' in text
    assert '**Narrator** · 8:00 AM  \n\nThe barista nods.' in text
    assert 'Lost words' not in text
    assert '<p class="note">You arrive at the cafe. <time>8:00 AM</time></p>' in exported(client, 'story').text


def test_an_empty_chat_still_exports(client, chat):
    page = exported(client, f"chat/{chat['timeline']}").text
    assert 'Chat · No messages yet' in page and 'Nothing was said here yet.' in page
    text = exported(client, f"chat/{chat['timeline']}", 'md').text
    assert text.endswith('*Nothing was said here yet.*\n')


def test_unknown_chats_and_formats_are_refused(client, chat):
    assert client.get('/api/export/chat/nope').status_code == 404
    assert client.get(f"/api/export/chat/{chat['timeline']}", params={'format': 'docx'}).status_code == 422


def test_filenames_keep_any_name_safely(clock):
    transcript = export.Transcript('Zoë / "Z"', 'chat', 'UTC', clock.now(), [])
    name = export.filename(transcript, 'html')
    assert name == 'Zoë Z - chat - 2026-10-05.html'
    assert export.disposition(name) == (
        'attachment; filename="Zo Z - chat - 2026-10-05.html"; '
        "filename*=UTF-8''Zo%C3%AB%20Z%20-%20chat%20-%202026-10-05.html")
