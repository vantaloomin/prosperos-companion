"""Text replies through the installed Codex CLI and its existing ChatGPT login.

Copied from prosperos-study server/providers/codex.py at bbcbde4. Changes: the conversation is
sent as one transcript on stdin, events are Companion `Chunk`s, and the temporary folder carries
the Companion's name. The CLI runs in an empty read-only folder with shell, plugins, MCP servers
and web search disabled; this app never reads or stores the login.
"""
import asyncio
import json
import shutil
import tempfile

from companion.errors import DomainError, require
from companion.providers.events import Chunk
from companion.providers.requests import transcript


def codex_arguments(executable: str, config: dict, directory: str) -> list[str]:
    arguments = [executable, 'exec', '--ignore-user-config', '--ephemeral', '--skip-git-repo-check',
                 '--sandbox', 'read-only', '--json', '--color', 'never', '--cd', directory,
                 '--model', config['model'], '-c', 'approval_policy="never"',
                 '-c', 'web_search="disabled"', '-c', 'mcp_servers={}']
    for feature in ('shell_tool', 'unified_exec', 'plugins', 'remote_plugin', 'skill_search'):
        arguments.extend(['--disable', feature])
    arguments.extend(['--enable', 'skip_host_skill_discovery'])
    if config.get('reasoning_effort'):
        arguments.extend(['-c', f'model_reasoning_effort="{config["reasoning_effort"]}"'])
    return [*arguments, '-']


def executable_path() -> str:
    executable = shutil.which('codex')
    require(bool(executable), 'Codex CLI was not found. Install it and sign in with codex login.', 409)
    return executable


def codex_event(data: dict) -> Chunk:
    kind = data.get('type')
    if kind == 'item.completed':
        item = data.get('item', {})
        if item.get('type') == 'agent_message':
            return Chunk(item.get('text', ''))
    if kind == 'turn.completed':
        return Chunk('', 'stop', done=True, usage=data.get('usage', {}))
    if kind in {'error', 'turn.failed'}:
        raise DomainError('Codex could not complete the request. Check its login, model, and CLI version.', 502,
                          'provider')
    return Chunk()


async def codex_output(process):
    """Codex reports whole messages; only the last one is the reply."""
    last_message = ''
    completed = False
    async for line in process.stdout:
        event = codex_event(json.loads(line))
        if event.text:
            last_message = event.text
        if event.done:
            completed = True
            yield Chunk(last_message, 'stop', done=True, usage=event.usage)
    require(await process.wait() == 0 and completed,
            'Codex exited before completing the response. Check its login and model.', 502)


class CodexProvider:
    async def stream(self, config: dict, _key: str | None, system: str, messages: list[dict]):
        executable = executable_path()
        with tempfile.TemporaryDirectory(prefix='companion-codex-') as directory:
            process = await asyncio.create_subprocess_exec(
                *codex_arguments(executable, config, directory), stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, cwd=directory,
                limit=2_000_000)
            try:
                async with asyncio.timeout(config['timeout_seconds']):
                    process.stdin.write(transcript(system, messages).encode())
                    await process.stdin.drain()
                    process.stdin.close()
                    async for event in codex_output(process):
                        yield event
            except TimeoutError as error:
                raise DomainError('Codex reached the configured time limit.', 504, 'timeout') from error
            except (ValueError, KeyError) as error:
                raise DomainError('This Codex CLI output format was not recognized.', 502) from error
            finally:
                if process.returncode is None:
                    process.kill()
                    await process.wait()

    async def check(self, _config: dict, _key: str | None) -> dict:
        process = await asyncio.create_subprocess_exec(executable_path(), 'login', 'status',
                                                       stdout=asyncio.subprocess.DEVNULL,
                                                       stderr=asyncio.subprocess.DEVNULL)
        try:
            code = await asyncio.wait_for(process.wait(), 15)
            require(code == 0, 'Codex is not signed in. Run codex login in your terminal.', 409)
            return {'available': True, 'models': [], 'model_details': [], 'generated': False,
                    'note': 'CLI login is available. Model access is checked when you send a message.'}
        except TimeoutError as error:
            process.kill()
            await process.wait()
            raise DomainError('The Codex login check timed out.', 504) from error
