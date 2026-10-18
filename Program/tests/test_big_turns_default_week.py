"""Back to school for a companion on the gentle default day (companion/life/big_turns.py `reshaped`)."""
from test_big_turns import begun, next_stage
from test_chapters import current

from companion.life import body, storylines
from companion.models import CharacterDefinition


def test_a_class_carved_from_the_default_day_leaves_every_block_with_its_days(client, clock, monkeypatch):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(storylines, 'STORIES', ())
    response = client.post('/api/companion', json={'name': 'Mira Lane', 'timezone': 'UTC', 'identity': 'Mira is 34.',
                                                    'location': 'Fells Point, Baltimore', 'money': {'career': 'accountant'}})
    assert response.status_code == 200, response.text
    chapter = begun(client, monkeypatch, clock, 'school')
    next_stage(client, clock, chapter['id'])
    definition = current(client)['version']['definition']
    assert any(block['kind'] == 'study' for block in definition['schedule'])
    # The Character page reads each block's days; a block without them broke the whole page.
    assert all(block.get('days') and 'themes' in block for block in definition['schedule']), definition['schedule']
    CharacterDefinition.model_validate(definition)
