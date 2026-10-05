"""The client against servers built with the official MCP Python SDK.

Set MCP_SDK_PYTHON to an interpreter with the SDK installed (CI's interop job pins the version);
without it these tests are skipped, since the SDK is not one of the app's dependencies.
"""
import asyncio
import os
import socket
import subprocess
import time
from pathlib import Path

import pytest

from companion.mcp import client as mcp

SDK_PYTHON = os.environ.get('MCP_SDK_PYTHON')
SERVER = str(Path(__file__).parent / 'interop' / 'sdk_server.py')
pytestmark = pytest.mark.skipif(not SDK_PYTHON, reason='MCP_SDK_PYTHON is not set')


async def forecast(transport):
    async with mcp.open_session(transport, timeout=20) as session:
        tools = {tool['name'] for tool in await session.list_tools()}
        result = await session.call_tool('get_forecast', {'location': 'Baltimore, MD'})
        with pytest.raises(mcp.ToolFailure) as failure:
            await session.call_tool('broken', {})
        return session.server, tools, result, failure.value.code


def check(outcome):
    server, tools, result, failure = outcome
    assert server['name'] == 'sdk-weather'
    assert server['protocol'] in mcp.ACCEPTED_VERSIONS
    assert {'get_forecast', 'broken'} <= tools
    assert result['text'] == 'Baltimore, MD: clear, high 70°F, low 55°F (for 1 day).'
    assert failure == 'tool_error'


def test_stdio():
    check(asyncio.run(forecast(mcp.StdioTransport([SDK_PYTHON, SERVER, 'stdio']))))


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


@pytest.mark.parametrize('mode,state', [('json', 'stateful'), ('sse', 'stateful'), ('json', 'stateless'),
                                        ('sse', 'stateless')])
def test_streamable_http(mode, state):
    port = free_port()
    process = subprocess.Popen([SDK_PYTHON, SERVER, 'http', str(port), mode, state])
    try:
        for _attempt in range(100):
            try:
                socket.create_connection(('127.0.0.1', port), timeout=0.5).close()
                break
            except OSError:
                time.sleep(0.1)
        check(asyncio.run(forecast(mcp.HttpTransport(f'http://127.0.0.1:{port}/mcp'))))
    finally:
        process.terminate()
        process.wait(timeout=10)
