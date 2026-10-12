"""The Claude Code provider against a stand-in `claude` CLI: the real CLI and a real Claude login are not used."""
import asyncio
import json
import sys
import textwrap

import pytest

from companion.errors import DomainError
from companion.providers import claude_code
from companion.providers.config import ProfileConfig

# Prints the stream a `claude -p --output-format stream-json --include-partial-messages` turn writes, and
# records what it was given in seen.json beside itself.
STAND_IN = '''
import json, os, sys
from pathlib import Path
arguments = sys.argv[1:]
if arguments[:2] == ["auth", "status"]:
    state = os.environ.get("STAND_IN_LOGIN", "in")
    print(json.dumps({"loggedIn": state != "out", "authMethod": "api_key" if state == "key" else "claude.ai"}))
    sys.exit(1 if state == "out" else 0)
system = Path(arguments[arguments.index("--system-prompt-file") + 1]).read_text(encoding="utf-8")
seen = {"arguments": arguments, "system": system, "stdin": sys.stdin.read(), "cwd": os.getcwd(),
        "api_key": os.environ.get("ANTHROPIC_API_KEY")}
Path(__file__).with_name("seen.json").write_text(json.dumps(seen))
mode = os.environ.get("STAND_IN_MODE", "stream")
print(json.dumps({"type": "system", "subtype": "init"}))
if mode == "login":
    print(json.dumps({"type": "result", "subtype": "success", "is_error": True,
                      "result": "Not logged in. Please run /login"}))
    sys.exit(1)
if mode == "stream":
    for piece in ("Hello ", "there."):
        print(json.dumps({"type": "stream_event", "event": {"type": "content_block_delta",
                                                            "delta": {"type": "text_delta", "text": piece}}}))
    print(json.dumps({"type": "stream_event", "event": {"type": "content_block_delta",
                                                        "delta": {"type": "thinking_delta", "thinking": "hm"}}}))
print("")
print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "Hello there.",
                  "usage": {"input_tokens": 12, "output_tokens": 3}}))
'''


@pytest.fixture
def stand_in(tmp_path, monkeypatch):
    script = tmp_path / 'claude_stand_in.py'
    script.write_text(textwrap.dedent(STAND_IN), encoding='utf-8')
    original = asyncio.create_subprocess_exec

    async def run(executable, *arguments, **options):
        return await original(executable, str(script), *arguments, **options)
    monkeypatch.setattr(claude_code, 'executable_path', lambda _config: sys.executable)
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', run)
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-ant-not-for-the-cli')
    return tmp_path


def config(**changes):
    return {'provider': 'claude_code', 'model': 'sonnet', 'timeout_seconds': 30, **changes}


def reply(**changes):
    async def collect():
        return [chunk async for chunk in claude_code.ClaudeCodeProvider().stream(
            config(**changes), None, 'You are Sally.', [{'role': 'user', 'content': 'Hi'},
                                                        {'role': 'assistant', 'content': 'Hey!'},
                                                        {'role': 'user', 'content': 'How are you?'}])]
    return asyncio.run(collect())


def test_a_reply_streams_from_claude_p_with_tools_off_and_the_plan_login(stand_in):
    chunks = reply(reasoning_effort='low')
    assert ''.join(chunk.text for chunk in chunks) == 'Hello there.'
    assert chunks[-1].done and chunks[-1].usage == {'input_tokens': 12, 'output_tokens': 3}
    seen = json.loads((stand_in / 'seen.json').read_text())
    arguments = seen['arguments']
    assert arguments[0] == '-p' and '--bare' not in arguments
    assert arguments[arguments.index('--tools') + 1] == ''
    assert arguments[arguments.index('--model') + 1] == 'sonnet'
    assert arguments[arguments.index('--effort') + 1] == 'low'
    assert {'--strict-mcp-config', '--disable-slash-commands', '--no-session-persistence'} <= set(arguments)
    assert seen['system'] == 'You are Sally.'
    assert seen['stdin'] == 'User: Hi\n\nAssistant: Hey!\n\nUser: How are you?\n\nAssistant:'
    assert 'companion-claude-' in seen['cwd']
    assert seen['api_key'] is None  # a key set for the Anthropic provider never replaces the plan


def test_a_cli_that_does_not_stream_still_gives_the_whole_reply(stand_in, monkeypatch):
    monkeypatch.setenv('STAND_IN_MODE', 'whole')
    chunks = reply()
    assert [chunk.text for chunk in chunks] == ['Hello there.'] and chunks[0].done


def test_a_missing_login_says_how_to_sign_in(stand_in, monkeypatch):
    monkeypatch.setenv('STAND_IN_MODE', 'login')
    with pytest.raises(DomainError) as raised:
        reply()
    assert raised.value.message == claude_code.LOGIN_STEP


def test_test_connection_checks_the_login_and_lists_the_model_names(stand_in, monkeypatch):
    provider = claude_code.ClaudeCodeProvider()
    result = asyncio.run(provider.check(config(), None))
    assert result['models'] == ['sonnet', 'opus', 'haiku', 'fable'] and result['location'] == sys.executable
    assert result['model_details'][0]['supported_efforts'] == list(claude_code.EFFORTS)
    assert 'signed in' in result['note'] and 'API key' not in result['note']
    monkeypatch.setenv('STAND_IN_LOGIN', 'key')
    assert 'billed to that key' in asyncio.run(provider.check(config(), None))['note']
    monkeypatch.setenv('STAND_IN_LOGIN', 'out')
    with pytest.raises(DomainError) as raised:
        asyncio.run(provider.check(config(), None))
    assert raised.value.message == claude_code.LOGIN_STEP


def test_the_profile_takes_a_full_cli_location_and_plan_efforts_only():
    profile = ProfileConfig(provider='claude_code', model='opus', reasoning_effort='max',
                            cli_path=sys.executable)
    assert profile.base_url == '' and profile.cli_path == sys.executable
    for bad in ({'cli_path': 'claude'}, {'reasoning_effort': 'minimal'}, {'temperature': 0.5}):
        with pytest.raises(ValueError):
            ProfileConfig(provider='claude_code', model='opus', **bad)
    with pytest.raises(ValueError):
        ProfileConfig(provider='codex', model='gpt-5.5', cli_path=sys.executable)


def test_a_cli_location_that_does_not_exist_is_reported(tmp_path):
    with pytest.raises(DomainError) as raised:
        claude_code.executable_path({'cli_path': str(tmp_path / 'missing' / 'claude')})
    assert 'location set in this profile' in raised.value.message
