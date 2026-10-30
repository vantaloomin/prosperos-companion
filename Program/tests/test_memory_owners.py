"""Whose fact a model-found memory is: a kind of animal or thing is never someone in the user's life."""
import pytest

from companion.memory.owners import belongs


@pytest.mark.parametrize('subject, text, names', [
    ("Mom's home", 'my mom lives in Towson', ()),
    ("Jo's job", 'Jo works at the library now', ()),
    ("Jo's job", 'I had lunch with Jo who works at the library', ()),
    ("Jo's job", 'Jo got a job at the library', ()),
    ("Chris's job", 'Chris teaches piano on weekends', ()),
    ("Dog's name", 'my dog is called Pepper', ()),
    ("Our bats' home", 'our bats live in the attic', ()),
    ("Kitty's favourite", 'she loves tuna', ('Kitty',)),
    ("Sett's gift", 'you gave me that ring', ('Sett',)),
    ('Hobby', 'pottery class every week', ()),
    ("User's job", 'I teach 8th grade science', ()),
])
def test_people_and_pets_in_the_users_life(subject, text, names):
    assert belongs(subject, text, names)


@pytest.mark.parametrize('subject, text', [
    ("Bats' diet", 'we watched the bats tonight, bats eat mosquitoes and flies'),
    ("Bats' home", 'Bats live in the attic and come out at dusk'),
    ("Bats' home", 'Bats lived in the attic for years'),
    ("Dogs' diet", 'dogs eat meat mostly'),
    ("Owls' habits", 'Owls hunt at night, which is wild'),
    ("Mice's home", 'Mice nest in the shed'),
])
def test_kinds_of_animals_and_things(subject, text):
    assert not belongs(subject, text)
