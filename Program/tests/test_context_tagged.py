"""The tagged prompt layout says whose each section is, so small models keep her news and the user's apart."""
from companion.memory.context import HEADINGS, OWNER, Packet, render


def packet():
    packet = Packet(10_000)
    packet.require('character', 'v1', 'You are Mya.')
    packet.require('time', 'clock', 'Your local time: 09:00.')
    packet.offer('profile', 'm1', '- Name: Sam')
    packet.offer('storylines', 's1', '- You got the charge nurse promotion.')
    packet.offer('circle', 'p1', '- Ashley (sister)')
    return packet


def test_every_section_has_an_owner():
    assert set(HEADINGS) <= set(OWNER)


def test_tagged_sections_carry_their_owner_and_heading():
    system = render(packet(), [], 'tagged', 'Mya')['system']
    assert system.startswith('<character>\nYou are Mya.\n</character>')
    assert 'about="you" is about you, Mya' in system
    assert '<user_profile about="user">\nWhat you know about the user:\n- Name: Sam\n</user_profile>' in system
    assert '<storylines about="you">' in system and '<your_circle about="your_people">' in system
    assert system.index('<user_profile') < system.index('<storylines') < system.index('<time_now')
    assert '## ' not in system


def test_headings_stay_the_default():
    rendered = render(packet(), [])
    assert '## What you know about the user\n- Name: Sam' in rendered['system']
    assert '<user_profile' not in rendered['system'] and rendered['receipt']['layout'] == 'headings'
