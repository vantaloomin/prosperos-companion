"""Acceptance fixtures from the PRD's memory rows: personal memory over time, formation and authority,
immediate correction, and forgetting and restore.

Each fixture scripts what the user says and checks current values and historical answers separately;
elapsed age is never the truth rule.
"""
import re
from datetime import timedelta
from pathlib import Path

import pytest
from conftest import send

from companion import backup, workspace
from companion.errors import DomainError
from companion.memory import records
from companion.memory.formation import run_pending
from companion.models import MemoryCorrection, SettingsUpdate

DAY = timedelta(days=1)


def say(client, text, counter=[0]):
    counter[0] += 1
    result = send(client, text, f'fixture-{counter[0]:06d}')
    assert client.post('/api/memory/run').status_code == 200
    return result


def section(system: str, heading: str) -> str:
    """A section's lines, with those new in this conversation (in the reply's notes)."""
    found = re.findall(rf'## {re.escape(heading)}(?: \(new in this conversation\))?\n(.*?)(?=\n## |\Z)', system, re.S)
    return '\n'.join(found)


def preview(client) -> str:
    response = client.get('/api/context/preview')
    assert response.status_code == 200, response.text
    return response.json()['prompt']


def current(client, subject) -> list[str]:
    return [item['value'] for item in client.get('/api/memories').json()
            if item['subject'] == subject and item['current']]


def test_personal_memory_over_twelve_months(client, connected, clock):
    """A move, a changed preference, a passing mood, postponed plans, a resolved disagreement and a
    months-old relevant fact, across twelve simulated months."""
    client.put('/api/settings', json={'automatic_memory': True, 'user_timezone': 'America/New_York'})

    # Month 0 (Monday 5 October 2026).
    say(client, 'I live in Chicago. My favourite tea is genmaicha. My sister is called Ana.')
    disagreement = client.post('/api/memories', json={
        'layer': 'relationship', 'subject': 'Disagreement about plans',
        'value': 'We argued about cancelled plans; not resolved yet'}).json()
    # A passing mood that must not become identity.
    say(client, "I'm exhausted today")
    assert 'Exhausted' in section(preview(client), "The user's current circumstances")
    clock.advance(2 * DAY)
    assert 'Exhausted' not in preview(client)

    # Month 1: a plan, then a postponement.
    clock.advance(28 * DAY)
    say(client, 'I have an interview next Thursday')
    [interview] = [item for item in client.get('/api/memories').json() if item['subject'] == 'Interview']
    assert interview['plan_status'] == 'agreed'
    say(client, 'My interview got postponed to the 20th of November')
    [interview] = [item for item in client.get('/api/memories').json() if item['subject'] == 'Interview']
    assert interview['plan_status'] == 'postponed' and interview['applies_from'].startswith('2026-11-20')

    # The disagreement is resolved by the user's correction.
    client.post(f"/api/memories/{disagreement['id']}/correct",
                json={'value': 'We talked it through; resolved, no hard feelings', 'expected_revision': 1})

    # Month 3: a move. Month 4: a possible move. Month 5: an old home.
    clock.advance(60 * DAY)
    say(client, 'I moved to Boston last week')
    clock.advance(30 * DAY)
    say(client, 'I might move to Denver')
    clock.advance(30 * DAY)
    say(client, 'I lived in Seattle ten years ago')

    # Month 7: a changed preference.
    clock.advance(60 * DAY)
    say(client, 'These days my favourite tea is hojicha')

    # Month 12.
    clock.advance(150 * DAY)
    system = preview(client)
    profile = section(system, 'What you know about the user')
    commitments = section(system, 'Open plans and commitments')

    # Current values.
    assert current(client, 'Home city') == ['Boston']
    assert 'Home city: Boston' in profile
    assert 'Chicago' not in profile and 'Seattle' not in profile
    assert 'Favourite tea: hojicha' in profile and 'genmaicha' not in profile
    people = section(system, "People in the user's real life (what the user told you about them; you have never met "
                             'them, so never invent details about them or claim to know them yourself)')
    assert "Ana (the user's sister)" in people, 'a months-old fact stays in the context'
    assert 'Might move to Denver [proposed]' in commitments
    assert 'Interview' in commitments and 'outcome not confirmed' in commitments, \
        'the date passing does not prove the interview happened'
    assert 'Exhausted' not in system
    resolved = [item for item in client.get('/api/memories').json() if item['layer'] == 'relationship']
    assert [item['value'] for item in resolved] == ['We talked it through; resolved, no hard feelings']

    # Historical answers: earlier homes and the earlier preference stay recallable history.
    say(client, 'Remind me, what was it like when I lived in Chicago?')
    recalled = section(preview(client), 'Possibly relevant memories')
    assert 'Home city: Chicago [no longer current]' in recalled
    homes = {item['value']: item for item in client.get('/api/memories').json() if item['subject'] == 'Home city'}
    assert homes['Chicago']['ended_by_id'] == homes['Boston']['id']
    assert homes['Seattle']['current'] is False and homes['Seattle']['dates_uncertain'] is True
    assert homes['Seattle']['ended_by_id'] is None, 'an old home never ends the current one'
    say(client, 'Which tea did I like before hojicha? Was it genmaicha?')
    assert 'genmaicha [no longer current]' in section(preview(client), 'Possibly relevant memories')


def test_memory_formation_and_authority(client, connected, provider):
    """Automatic memory off/on, Remember/Don't remember, sensitive permission, hypothetical and roleplayed
    statements and companion guesses: only permitted, supported records are committed."""
    from companion.providers.chat import Chunk

    settings = client.get('/api/settings').json()
    assert settings['automatic_memory'] and settings['sensitive_memory'], 'memory is opt-out'
    client.put('/api/settings', json={'automatic_memory': False, 'sensitive_memory': False})
    say(client, 'I live in Lisbon')
    assert client.get('/api/memories').json() == [], 'nothing is saved with automatic memory off'

    client.put('/api/settings', json={'automatic_memory': True})
    say(client, 'Hypothetically, I live on the moon')
    say(client, '*draws her sword* I am the queen of Narnia and I live in Cair Paravel')
    say(client, 'My character said "I work as a spy"')
    provider.replies = [[Chunk('I bet you love jazz and live in Paris.'), Chunk('', 'stop')]]
    guess = say(client, 'Guess something about me')['reply']
    assert client.get('/api/memories').json() == []
    assert guess['role'] == 'companion', 'Remember this on it keeps what she said (tests/test_memory_formation.py)'

    # A model interpretation stays tentative and out of context until confirmed.
    tentative = client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Music',
                                                   'value': 'Might like jazz', 'tentative': True}).json()
    assert 'jazz' not in preview(client)
    assert tentative['authority'] == 'tentative'

    # With sensitive memory off, sensitive facts need permission; deliberate Remember this is that permission.
    say(client, "I'm allergic to shellfish")
    assert [item['reason'] for item in client.get('/api/memory/suggestions').json()] == ['sensitive']
    message = say(client, "I'm allergic to penicillin")['message']
    client.post(f"/api/conversation/messages/{message['id']}/remember")
    allergies = [item['value'] for item in client.get('/api/memories').json() if item['subject'] == 'Allergy']
    assert allergies == ['penicillin']

    # Don't remember this, then the statement repeated elsewhere is still allowed.
    declined = say(client, 'My favourite film is Heat')['message']
    client.post(f"/api/conversation/messages/{declined['id']}/decline-memory")
    assert not [item for item in client.get('/api/memories').json() if item['subject'] == 'Favourite film']
    committed = {(item['subject'], item['value'], item['authority']) for item in client.get('/api/memories').json()}
    assert committed == {('Allergy', 'penicillin', 'stated'), ('Music', 'Might like jazz', 'tentative')}


def test_immediate_correction(client, app, connected, provider):
    """A correction saved while consolidation work and a reply are in flight: the next reply uses the new
    revision, stale work cannot commit, history stays labelled and a failed save stays visible."""
    database = app.state.database
    client.put('/api/settings', json={'automatic_memory': True})
    say(client, 'I live in Chicago')
    [chicago] = client.get('/api/memories').json()

    # Queue extraction for a message, then correct while the reply to it is being written.
    send(client, 'My favourite tea is genmaicha', 'correction-0001')
    provider.before_finish = lambda: records.correct(
        database, chicago['id'], MemoryCorrection(value='Boston', expected_revision=1))
    stale = send(client, 'Tell me about my city', 'correction-0002')['reply']
    assert stale['status'] == 'withheld'
    provider.before_finish = None

    # The queued job was planned before; turning automatic memory off in between makes it stale.
    client.put('/api/settings', json={'automatic_memory': False})
    assert run_pending(database)['stale'] == 2
    assert not [item for item in client.get('/api/memories').json() if item['subject'] == 'Favourite tea']

    # The next reply uses the corrected value.
    send(client, 'Hello again', 'correction-0003')
    assert 'Home city: Boston' in provider.requests[-1]['prompt']
    assert 'Chicago' not in provider.requests[-1]['prompt']

    # The original wording remains as labelled history.
    history = {item['value']: item['status'] for item in client.get('/api/memories?history=true').json()}
    assert history == {'Chicago': 'superseded', 'Boston': 'active'}

    # A correction against an old revision fails visibly and changes nothing.
    response = client.post(f"/api/memories/{chicago['id']}/correct", json={'value': 'Denver', 'expected_revision': 1})
    assert response.status_code == 409
    assert [item['value'] for item in client.get('/api/memories').json()] == ['Boston']


def test_forgetting_and_restore(client, app, connected, tmp_path, clock):
    """Excluding blocks every recall path; deleting removes records, sources, suggestions and receipts;
    a restore discloses that it may hold forgotten material and requires review."""
    client.put('/api/settings', json={'automatic_memory': True})
    # A name no generated character can have: the companion's circle draws on real given names.
    secret = say(client, 'My sister is called Ottoline')['message']
    for index in range(30):
        send(client, f'Small talk {index}', f'forget-{index:04d}')
    [sister] = client.get('/api/memories').json()

    # Exclusion: neither the memory nor its source message reaches the model.
    client.post(f"/api/memories/{sister['id']}/exclude")
    say(client, 'What is my sister called again, Ottoline?')
    request = client.get('/api/context/preview').json()
    assert 'Ottoline' not in request['prompt']
    assert 'My sister is called Ottoline' not in str(request)

    # A backup taken now still holds what is about to be deleted.
    archive = client.post('/api/backups').json()
    send(client, 'I live in Porto', 'forget-queued')

    # Deletion with sources: records, transcript text, suggestions, search and receipts.
    client.post(f"/api/memories/{sister['id']}/include")
    result = client.post(f"/api/memories/{sister['id']}/delete", json={'delete_sources': True}).json()
    assert result['redacted_message_ids'] == [secret['id']]
    assert client.get('/api/memories?history=true').json() == []
    assert client.get('/api/conversation/search', params={'q': 'sister is called'}).json()['results'] == []
    with app.state.database.connect() as connection:
        leftovers = [row[0] for row in connection.execute(
            "SELECT proposal FROM memory_candidates UNION ALL SELECT COALESCE(detail, '') FROM memory_activity "
            "UNION ALL SELECT COALESCE(receipt, '') FROM messages")]
        markers = {row[0] for row in connection.execute('SELECT target_id FROM deletion_markers')}
    assert not [text for text in leftovers if 'Ottoline' in text]
    assert sister['id'] in markers and secret['id'] in markers

    # Restoring the older backup into a fresh workspace: it may hold the forgotten fact, so it opens
    # paused with automatic memory off, review required, and queued extraction stale.
    restored = backup.restore(Path(archive['path']), tmp_path / 'restored' / 'companion.sqlite3', clock)
    with restored.connect() as connection:
        row = dict(connection.execute('SELECT * FROM workspace_settings').fetchone())
    assert row['review_required'] == 1 and row['automatic_memory'] == 0 and row['paused_at'] is not None
    with pytest.raises(DomainError):
        workspace.update(restored, SettingsUpdate(automatic_memory=True))
    workspace.update(restored, SettingsUpdate(automatic_memory=True, review_complete=True))
    result = run_pending(restored)
    assert result['processed'] == result['stale'] > 0, 'jobs queued before the backup never commit'
