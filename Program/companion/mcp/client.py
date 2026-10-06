"""A small, read-only MCP client for current-context tools (PRD X1-X3).

It speaks the handshake protocol revisions (2025-03-26 to 2025-11-25) over two transports:
stdio (a local program the user configured, one JSON-RPC message per line) and streamable HTTP
(JSON or server-sent event responses, with an optional session id). It only lists and calls
tools. Requests a server sends back (sampling, roots, elicitation) are refused, so a server can
never ask the app's model or the user anything through this client.

Every session is short: open, initialize, one or two requests, close. Each request has a
deadline and each message a size cap; nothing here retries, which is the lookup policy's job.
"""
import asyncio
import json
import os
import subprocess
import sys
import threading
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

import httpx

from companion.identity import APP_NAME, VERSION
from companion.providers.urls import is_loopback

PROTOCOL_VERSION = '2025-11-25'
ACCEPTED_VERSIONS = ('2025-11-25', '2025-06-18', '2025-03-26')
MAX_MESSAGE_BYTES = 512_000
MAX_TOOLS = 200
# Variables a local tool program commonly needs to start. Nothing else from the app's own
# environment (such as COMPANION_API_KEY) is passed on.
INHERITED_ENV = ('PATH', 'PATHEXT', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'TEMP', 'TMP', 'TMPDIR', 'HOME',
                 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'PROGRAMDATA', 'LANG', 'LC_ALL')


class ToolFailure(Exception):
    """A lookup that did not produce a usable result. `code` is stable and safe to show."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def check_url(url: str):
    parts = urlsplit(url)
    if not parts.hostname or (parts.scheme != 'https' and not (parts.scheme == 'http' and is_loopback(parts.hostname))):
        raise ToolFailure('invalid_address', 'Use an HTTPS server address, or HTTP for a service on this computer.')
    if parts.username or parts.password:
        raise ToolFailure('invalid_address', 'Put credentials in the key field, not in the server address.')


class StdioTransport:
    """A local program on stdin/stdout. Threads do the blocking I/O so any event loop works."""

    def __init__(self, command: list[str], env: dict | None = None):
        self.command = command
        self.env = env or {}
        self.process = None
        self.lines: asyncio.Queue | None = None

    async def open(self):
        environment = {key: os.environ[key] for key in INHERITED_ENV if key in os.environ} | self.env
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        try:
            self.process = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                            stderr=subprocess.DEVNULL, env=environment, creationflags=flags)
        except OSError as error:
            raise ToolFailure('start_failed', f'The tool program could not start: {error.strerror or error}.') from error
        loop, self.lines = asyncio.get_running_loop(), asyncio.Queue()
        threading.Thread(target=self.read, args=(loop,), daemon=True).start()

    def read(self, loop):
        stream = self.process.stdout
        while True:
            line = stream.readline(MAX_MESSAGE_BYTES + 1)
            if not line:
                break
            if len(line) > MAX_MESSAGE_BYTES:
                loop.call_soon_threadsafe(self.lines.put_nowait, ToolFailure('too_large', 'The tool sent too much data.'))
                break
            loop.call_soon_threadsafe(self.lines.put_nowait, line)
        loop.call_soon_threadsafe(self.lines.put_nowait, None)

    async def send(self, message: dict) -> list[dict]:
        data = (json.dumps(message, separators=(',', ':')) + '\n').encode()
        try:
            await asyncio.to_thread(self.write, data)
        except (BrokenPipeError, OSError) as error:
            raise ToolFailure('transport', 'The tool program stopped.') from error
        return []

    def write(self, data: bytes):
        self.process.stdin.write(data)
        self.process.stdin.flush()

    async def receive(self) -> dict:
        while True:
            line = await self.lines.get()
            if line is None:
                raise ToolFailure('transport', 'The tool program stopped.')
            if isinstance(line, ToolFailure):
                raise line
            if line.strip():
                return parse_message(line)

    async def close(self):
        if self.process is None:
            return
        process = self.process
        await asyncio.to_thread(stop_process, process)


def stop_process(process):
    try:
        process.stdin.close()
    except OSError:
        pass
    try:
        process.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()


def parse_message(raw) -> dict:
    try:
        message = json.loads(raw)
    except ValueError as error:
        raise ToolFailure('protocol', 'The tool sent a message that is not JSON-RPC.') from error
    if not isinstance(message, dict) or message.get('jsonrpc') != '2.0':
        raise ToolFailure('protocol', 'The tool sent a message that is not JSON-RPC.')
    return message


class HttpTransport:
    """Streamable HTTP: each request is a POST answered with JSON or a server-sent event stream."""

    def __init__(self, url: str, headers: dict | None = None, client: httpx.AsyncClient | None = None):
        check_url(url)
        self.url = url
        self.headers = headers or {}
        self.client = client
        self.owns_client = client is None
        self.session_id = None
        self.protocol = None
        self.pending: list[dict] = []

    async def open(self):
        if self.client is None:
            self.client = httpx.AsyncClient(follow_redirects=False, timeout=httpx.Timeout(30, connect=10))

    def request_headers(self) -> dict:
        headers = {'Accept': 'application/json, text/event-stream', 'Content-Type': 'application/json',
                   **self.headers}
        if self.session_id:
            headers['Mcp-Session-Id'] = self.session_id
        if self.protocol:
            headers['MCP-Protocol-Version'] = self.protocol
        return headers

    async def send(self, message: dict) -> list[dict]:
        try:
            async with self.client.stream('POST', self.url, json=message, headers=self.request_headers()) as response:
                return await self.read_response(response, message)
        except httpx.TimeoutException as error:
            raise ToolFailure('timeout', 'The server did not answer in time.') from error
        except httpx.HTTPError as error:
            raise ToolFailure('transport', 'The server could not be reached.') from error
        except ValueError as error:
            raise ToolFailure('protocol', 'The server sent a message that is not JSON-RPC.') from error

    async def read_response(self, response, message) -> list[dict]:
        if response.status_code in {401, 403}:
            raise ToolFailure('unauthorized', 'The server refused the request. Check its key.')
        if response.status_code == 404 and self.session_id:
            raise ToolFailure('transport', 'The server ended the session.')
        if response.status_code >= 300:
            raise ToolFailure('http_status', f'The server answered with HTTP {response.status_code}.')
        if session := response.headers.get('mcp-session-id'):
            self.session_id = session
        if response.status_code == 202 or 'id' not in message or 'method' not in message:
            return []
        kind = response.headers.get('content-type', '').split(';')[0].strip().lower()
        if kind == 'text/event-stream':
            return await self.read_events(response, message['id'])
        if kind == 'application/json':
            body = await read_limited(response)
            parsed = json.loads(body) if body else []
            return [parse_message(json.dumps(item)) for item in (parsed if isinstance(parsed, list) else [parsed])]
        raise ToolFailure('protocol', 'The server answered with an unexpected content type.')

    async def read_events(self, response, request_id) -> list[dict]:
        """Collect messages from an event stream until the response to `request_id` arrives."""
        messages, data, size = [], [], 0
        async for line in response.aiter_lines():
            size += len(line) + 1
            if size > MAX_MESSAGE_BYTES:
                raise ToolFailure('too_large', 'The server sent too much data.')
            if line.startswith('data:'):
                data.append(line[5:].removeprefix(' '))
            elif not line and data:
                message = parse_message('\n'.join(data))
                data = []
                messages.append(message)
                if message.get('id') == request_id and ('result' in message or 'error' in message):
                    return messages
        if data:
            messages.append(parse_message('\n'.join(data)))
        return messages

    async def receive(self) -> dict:
        if not self.pending:
            raise ToolFailure('protocol', 'The server did not answer the request.')
        return self.pending.pop(0)

    async def close(self):
        if self.session_id and self.client is not None:
            try:
                await self.client.delete(self.url, headers=self.request_headers(), timeout=3)
            except httpx.HTTPError:
                pass
        if self.owns_client and self.client is not None:
            await self.client.aclose()


async def read_limited(response) -> bytes:
    chunks, size = [], 0
    async for chunk in response.aiter_bytes():
        size += len(chunk)
        if size > MAX_MESSAGE_BYTES:
            raise ToolFailure('too_large', 'The server sent too much data.')
        chunks.append(chunk)
    return b''.join(chunks)


class Session:
    """One initialized connection. Use `open_session`."""

    def __init__(self, transport, timeout: float):
        self.transport = transport
        self.timeout = timeout
        self.next_id = 0
        self.server: dict = {}

    async def request(self, method: str, params: dict | None = None) -> dict:
        self.next_id += 1
        message = {'jsonrpc': '2.0', 'id': self.next_id, 'method': method}
        if params is not None:
            message['params'] = params
        try:
            return await asyncio.wait_for(self.exchange(message), self.timeout)
        except TimeoutError as error:
            raise ToolFailure('timeout', 'The tool did not answer in time.') from error

    async def exchange(self, message) -> dict:
        early = await self.transport.send(message)
        if isinstance(self.transport, HttpTransport):
            self.transport.pending.extend(early)
        while True:
            reply = await self.transport.receive()
            if 'method' in reply:
                await self.answer_server(reply)
                continue
            if reply.get('id') != message['id']:
                continue
            if 'error' in reply:
                error = reply['error'] if isinstance(reply['error'], dict) else {}
                raise ToolFailure('server_error', str(error.get('message') or 'The tool reported an error.')[:300])
            result = reply.get('result')
            if not isinstance(result, dict):
                raise ToolFailure('protocol', 'The tool sent a malformed result.')
            return result

    async def answer_server(self, message):
        """Notifications are ignored; a ping is answered; every other server request is refused."""
        if 'id' not in message:
            return
        if message['method'] == 'ping':
            reply = {'jsonrpc': '2.0', 'id': message['id'], 'result': {}}
        else:
            reply = {'jsonrpc': '2.0', 'id': message['id'],
                     'error': {'code': -32601, 'message': 'This client does not support server requests.'}}
        early = await self.transport.send(reply)
        if isinstance(self.transport, HttpTransport):
            self.transport.pending.extend(early)

    async def initialize(self):
        result = await self.request('initialize', {
            'protocolVersion': PROTOCOL_VERSION, 'capabilities': {},
            'clientInfo': {'name': APP_NAME, 'version': VERSION}})
        version = result.get('protocolVersion')
        if version not in ACCEPTED_VERSIONS:
            raise ToolFailure('unsupported_version', f'The server uses MCP version {str(version)[:20]}, '
                              'which this app does not support yet.')
        if 'tools' not in (result.get('capabilities') or {}):
            raise ToolFailure('no_tools', 'The server does not offer tools.')
        self.server = {'protocol': version, 'name': str((result.get('serverInfo') or {}).get('name', ''))[:120],
                       'version': str((result.get('serverInfo') or {}).get('version', ''))[:40]}
        if isinstance(self.transport, HttpTransport):
            self.transport.protocol = version
        await self.transport.send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})

    async def list_tools(self) -> list[dict]:
        tools, cursor = [], None
        for _page in range(10):
            result = await self.request('tools/list', {'cursor': cursor} if cursor else {})
            for tool in result.get('tools') or []:
                if isinstance(tool, dict) and isinstance(tool.get('name'), str):
                    tools.append({'name': tool['name'][:128], 'description': str(tool.get('description') or '')[:1000],
                                  'input_schema': tool.get('inputSchema') if isinstance(tool.get('inputSchema'), dict)
                                  else {'type': 'object'},
                                  'read_only': bool((tool.get('annotations') or {}).get('readOnlyHint'))})
            cursor = result.get('nextCursor')
            if not cursor or len(tools) >= MAX_TOOLS:
                break
        return tools[:MAX_TOOLS]

    async def call_tool(self, name: str, arguments: dict) -> dict:
        """Text content joined, plus structured content when the tool gives it. A tool error is a failure."""
        result = await self.request('tools/call', {'name': name, 'arguments': arguments})
        content = result.get('content') if isinstance(result.get('content'), list) else []
        texts = [item['text'] for item in content if isinstance(item, dict) and item.get('type') == 'text'
                 and isinstance(item.get('text'), str)]
        text = '\n'.join(texts)
        if result.get('isError'):
            raise ToolFailure('tool_error', (text or 'The tool reported an error.')[:300])
        structured = result.get('structuredContent')
        return {'text': text, 'structured': structured if isinstance(structured, dict) else None,
                'other_content': len(content) - len(texts)}


@asynccontextmanager
async def open_session(transport, timeout: float = 10):
    session = Session(transport, timeout)
    try:
        await transport.open()
        await session.initialize()
        yield session
    finally:
        await transport.close()
