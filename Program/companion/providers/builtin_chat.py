"""Built-in chat: a llama.cpp server the Companion starts on this PC for the chat model "Set it up for me" downloaded
(companion/ready.py).

It is built-in recall's server (builtin_recall.py) with a graphics-card build and a chat command: the whole model on
the card where it fits (llama.cpp fits what it can and runs the rest from memory), a context the size the profile
asks for, the model's own chat template and thinking off, since a companion's reply is a text message, not a puzzle.
The build is Vulkan on Windows, which runs on NVIDIA, AMD and Intel cards alike and is a 33 MB download beside about
650 MB for the CUDA build and its runtime; Apple silicon's build uses Metal, and an Intel Mac's runs on the processor.
The server keeps one port between launches, so the chat profile's address stays true and Settings > Models can test
it like any local server.
"""
import json
import socket
from pathlib import Path

from companion.providers.builtin_recall import RUNTIME_TAG, RUNTIMES, BuiltinRecall, free_port, threads

# Platform -> (asset, bytes, sha256). Checked by hand against the release on 2026-10-12.
GPU_RUNTIMES = {
    'windows-x64': (f'llama-{RUNTIME_TAG}-bin-win-vulkan-x64.zip', 33377746,
                    'd01301582c711a69b9747b5984710d6ca99e57d95f680d3d33753cec570b4cb6'),
    'macos-arm64': RUNTIMES['macos-arm64'],
    'macos-x64': RUNTIMES['macos-x64'],
}
CONTEXT = 16384
RESOURCE_GROUP = 'builtin-chat'


def state_file(root: Path) -> Path:
    return root / 'chat' / 'setup.json'


def read_state(root: Path) -> dict:
    """What "Set it up for me" has done on this computer (one file, shared by every world)."""
    try:
        found = json.loads(state_file(root).read_text('utf-8'))
    except (OSError, ValueError):
        return {}
    return found if isinstance(found, dict) else {}


def write_state(root: Path, state: dict):
    target = state_file(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + '.partial')
    partial.write_text(json.dumps(state, indent=2), 'utf-8')
    partial.replace(target)


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(('127.0.0.1', port))
        except OSError:
            return False
    return True


class BuiltinChat(BuiltinRecall):
    """Starts, watches and stops the built-in chat model's server."""
    build = '-gpu'
    label = 'built-in chat model'
    model_label = 'chat model'
    folder_name = 'chat'
    start_seconds = 300

    def assets(self) -> dict:
        return GPU_RUNTIMES

    def wanted(self) -> tuple[str, str] | None:
        state = read_state(self.database.root)
        server = self.server()
        if state.get('status') != 'ready' or not state.get('model_path') or not server:
            return None
        return server, state['model_path']

    def choose_port(self) -> int:
        """The port saved at setup, so the profile's address keeps working; a new one only when another program
        took it. Replies always ask the running server (companion/providers/chat.py `builtin_address`)."""
        state = read_state(self.database.root)
        port = state.get('port')
        if isinstance(port, int) and port_free(port):
            return port
        state['port'] = port = free_port()
        write_state(self.database.root, state)
        return port

    def command(self, server: str, model: str, port: int) -> list[str]:
        return [server, '-m', model, '--host', '127.0.0.1', '--port', str(port), '-ngl', '999', '-c', str(CONTEXT),
                '-t', str(max(threads(), 4)), '--jinja', '--reasoning-budget', '0', '--alias', Path(model).stem,
                '--no-webui']
