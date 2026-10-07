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
from companion.providers.capabilities import EFFORTS
from companion.providers.events import Chunk
from companion.providers.requests import transcript

# Shown when `codex app-server` cannot list models (an older CLI, or a failed call): the picker models in
# the Codex CLI's bundled catalog (codex-rs/models-manager/models.json at 746103b). A plan may not offer all.
FALLBACK_MODELS = ('gpt-6.1-sol', 'gpt-6-sol', 'gpt-6-astra', 'gpt-6-luna', 'gpt-5.6-sol', 'gpt-5.6-terra',
                   'gpt-5.6-luna', 'gpt-5.5')


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


def listed_model(item: dict) -> dict | None:
    """One `model/list` entry; `model` is the ID that `codex exec --model` takes."""
    identifier = item.get('model') or item.get('id')
    if not isinstance(identifier, str) or not identifier.strip() or item.get('hidden'):
        return None
    efforts = [option.get('reasoningEffort') for option in item.get('supportedReasoningEfforts') or []
               if isinstance(option, dict)]
    detail = {'id': identifier, 'name': str(item.get('displayName') or identifier), 'context_tokens': None,
              'max_output_tokens': None, 'limit_source': 'unreported'}
    return {**detail, 'supported_efforts': [effort for effort in EFFORTS if effort in efforts]} if efforts else detail


async def app_server_models(command: list[str], seconds: float = 20) -> list[dict]:
    """Ask `codex app-server` (JSON-RPC lines on stdio) for the models the current login can use."""
    with tempfile.TemporaryDirectory(prefix='companion-codex-') as directory:
        process = await asyncio.create_subprocess_exec(
            *command, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL, cwd=directory, limit=2_000_000)

        def send(message: dict):
            process.stdin.write((json.dumps(message) + '\n').encode())

        async def result(request_id: int, method: str, params: dict) -> dict:
            send({'id': request_id, 'method': method, 'params': params})
            await process.stdin.drain()
            while line := await process.stdout.readline():
                message = json.loads(line)
                if 'method' in message and 'id' in message:
                    send({'id': message['id'], 'error': {'code': -32601, 'message': 'Not supported.'}})
                elif message.get('id') == request_id:
                    require('error' not in message, 'Codex could not list its models.', 502)
                    return message['result']
            raise DomainError('Codex closed before listing its models.', 502)

        try:
            async with asyncio.timeout(seconds):
                await result(1, 'initialize', {'clientInfo': {'name': 'prosperos_companion',
                                                              'title': "Prospero's Companion", 'version': '0'}})
                send({'method': 'initialized'})
                models, cursor = [], None
                for page in range(1, 21):
                    data = await result(page + 1, 'model/list', {'cursor': cursor} if cursor else {})
                    models.extend(model for item in data['data'] if (model := listed_model(item)))
                    if not (cursor := data.get('nextCursor')):
                        return models
                return models
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()


async def codex_models(executable: str) -> tuple[list[dict], bool]:
    """The login's models, or the fallback list (and False) when the CLI cannot report them."""
    try:
        models = await app_server_models([executable, '-c', 'mcp_servers={}', 'app-server'])
        if models:
            return models, True
    except (DomainError, TimeoutError, OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    return [{'id': model, 'name': model, 'context_tokens': None, 'max_output_tokens': None,
             'limit_source': 'unreported'} for model in FALLBACK_MODELS], False


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
        executable = executable_path()
        process = await asyncio.create_subprocess_exec(executable, 'login', 'status',
                                                       stdout=asyncio.subprocess.DEVNULL,
                                                       stderr=asyncio.subprocess.DEVNULL)
        try:
            code = await asyncio.wait_for(process.wait(), 15)
            require(code == 0, 'Codex is not signed in. Run codex login in your terminal.', 409)
        except TimeoutError as error:
            process.kill()
            await process.wait()
            raise DomainError('The Codex login check timed out.', 504) from error
        models, reported = await codex_models(executable)
        note = ('The models your ChatGPT login can use, as the Codex CLI lists them.' if reported else
                'This Codex CLI did not list its models, so these are common Codex models; your plan may not '
                'include all of them. Model access is checked when you send a message.')
        return {'available': True, 'models': [model['id'] for model in models], 'model_details': models,
                'generated': False, 'note': note}
