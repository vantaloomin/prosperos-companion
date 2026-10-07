"""The chat prompt keeps what rarely changes first, so its start can be reused between replies."""
from companion.memory.context import HEADINGS, Packet, render

STABLE = ('boundaries', 'profile', 'self_facts', 'home')
PER_MESSAGE = ('time', 'wording', 'outside', 'recalled')


def test_sections_that_change_with_every_message_come_last():
    keys = list(HEADINGS)
    assert max(keys.index(key) for key in STABLE) < min(keys.index(key) for key in PER_MESSAGE)
    assert keys[-1] == 'recalled'


def test_the_prompt_starts_the_same_when_only_the_clock_and_recall_change():
    def system(clock, memory):
        packet = Packet(10_000)
        packet.require('character', 'v1', 'You are Mya.')
        packet.require('time', 'clock', clock)
        packet.offer('profile', 'm1', '- Name: Sam')
        packet.offer('circle', 'p1', '- Juniper (cat)')
        packet.offer('wording', 'wording', 'You keep repeating: "honestly". Say it differently.')
        packet.offer('recalled', 'm2', memory)
        return render(packet, [])['system']

    first = system('Your local time: 09:00.', '- Pottery class starts January 20')
    second = system('Your local time: 10:15.', '- Dana\'s puppy is named Waffles')
    shared = next(index for index, (a, b) in enumerate(zip(first, second)) if a != b)
    assert first[:shared].endswith('## Time\nYour local time: ')
    assert first.index('## What you know about the user') < first.index('## Time') < first.index('## Your wording')
    assert 'You keep repeating' not in first.split('\n\n')[0]
