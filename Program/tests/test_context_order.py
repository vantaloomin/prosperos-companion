"""The chat prompt keeps what rarely changes first, so its start can be reused between replies (prompt caching):
what changes with every message goes with the message being answered, not in the system prompt."""
from companion.memory.context import HEADINGS, NOTE_CLOSE, NOTE_OPEN, NOW, Packet, add_note, render, window_start

PER_MESSAGE = ('time', 'wording', 'outside', 'recalled', 'circle_now', 'wearing', 'intentions', 'photo')
# Saved during a chat: after what changes once a day, so a new memory leaves the start of the prompt alone.
GROWS = ('profile', 'people', 'self_facts', 'commitments')
DAILY = ('almanac', 'money', 'weather', 'body', 'wardrobe', 'circle')


def packet(clock, memory, wording='You keep repeating: "honestly". Say it differently.'):
    found = Packet(10_000)
    found.require('character', 'v1', 'You are Mya.')
    found.require('time', 'clock', clock)
    found.offer('profile', 'm1', '- Name: Sam')
    found.offer('circle', 'p1', '- Juniper (cat)')
    found.offer('circle_now', 'p1', '- Juniper: Right now: asleep on the radiator.')
    found.offer('wording', 'wording', wording)
    found.offer('recalled', 'm2', memory)
    return found


def test_sections_that_change_with_every_message_are_not_in_the_system_prompt():
    keys = list(HEADINGS)
    assert not set(PER_MESSAGE) & set(HEADINGS) and set(PER_MESSAGE) <= set(NOW)
    assert max(keys.index(key) for key in DAILY) < min(keys.index(key) for key in GROWS)
    assert list(NOW)[-1] == 'time'


def test_the_system_prompt_and_conversation_stay_the_same_when_only_the_clock_and_recall_change():
    conversation = [{'role': 'user', 'text': 'Hi!'}, {'role': 'companion', 'text': 'Hey you.'},
                    {'role': 'user', 'text': 'How was work?'}]
    first = render(packet('Your local time: 09:00.', '- Pottery class starts January 20'), conversation)
    second = render(packet('Your local time: 10:15.', '- Dana\'s puppy is named Waffles', 'Say it differently.'),
                    conversation)
    assert first['system'] == second['system'] and first['messages'][:2] == second['messages'][:2]
    assert '## What you know about the user\n- Name: Sam' in first['system']
    assert 'Juniper (cat)' in first['system'] and 'asleep on the radiator' not in first['system']
    latest = first['messages'][-1]
    assert latest['role'] == 'user' and latest['content'].startswith(NOTE_OPEN)
    assert latest['content'].endswith(f'{NOTE_CLOSE}\nHow was work?')
    assert latest['content'].index('## Your wording lately') < latest['content'].index('## Right now\nYour local time')
    assert first['history'][-1] == {'role': 'user', 'content': 'How was work?'}


def test_a_note_for_one_reply_joins_the_notes_and_a_first_text_gets_notes_of_its_own():
    conversation = [{'role': 'user', 'text': 'Night!'}, {'role': 'companion', 'text': 'Sleep well.'}]
    rendered = render(packet('Your local time: 08:00.', ''), conversation)
    assert rendered['messages'][:2] == rendered['history']
    assert rendered['messages'][-1] == {'role': 'user', 'content': f"{NOTE_OPEN}\n{rendered['note']}"}
    busy = add_note(rendered, 'You are at work: keep it short.')
    assert busy['system'] == rendered['system'] and busy['messages'][-1]['content'].endswith('keep it short.')


def test_the_conversation_starts_at_the_same_turn_for_several_replies():
    starts = [window_start(count) for count in range(1, 60)]
    assert starts[:20] == [0] * 20
    assert all(count - start >= min(count, 20) for count, start in zip(range(1, 60), starts))
    assert len(set(starts)) == 4 and all(start % 12 == 0 for start in starts)
