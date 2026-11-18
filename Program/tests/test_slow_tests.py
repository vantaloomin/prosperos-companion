"""The list of slow tests (tests/slow_tests.txt) only names tests that exist, so a renamed test is not quietly
run on every pull request again, or left out for good."""
import re
from pathlib import Path

from conftest import slow_tests

TESTS = Path(__file__).parent


def test_every_slow_test_listed_exists():
    listed = slow_tests()
    assert listed
    for file, name in sorted(listed):
        source = (TESTS / file).read_text(encoding='utf-8')
        assert re.search(rf'^(async )?def {re.escape(name)}\(', source, re.MULTILINE), f'{file}::{name} is not a test'
