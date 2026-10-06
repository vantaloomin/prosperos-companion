"""A weather tool served by the official MCP Python SDK, for the interoperability tests.

Runs under an interpreter that has `mcp` installed (not one of the app's dependencies):
`python sdk_server.py stdio` or `python sdk_server.py http PORT [json|sse] [stateful|stateless]`.
"""
import sys

from mcp.server.mcpserver import MCPServer

server = MCPServer('sdk-weather', version='1.0')


@server.tool()
def get_forecast(location: str, days: int = 1) -> str:
    """Current weather and forecast for a city."""
    return f'{location}: clear, high 70°F, low 55°F (for {days} day).'


@server.tool()
def broken() -> str:
    """Always fails."""
    raise RuntimeError('upstream unavailable')


if __name__ == '__main__':
    if sys.argv[1] == 'stdio':
        server.run('stdio')
    else:
        import uvicorn
        port, mode, state = int(sys.argv[2]), sys.argv[3], sys.argv[4]
        app = server.streamable_http_app(json_response=mode == 'json', stateless_http=state == 'stateless')
        uvicorn.run(app, host='127.0.0.1', port=port, log_level='warning')
