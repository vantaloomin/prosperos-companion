"""Start the stand-in model and ComfyUI (scripts/acceptance/standins.py) and one app per world, each on a fresh
data folder, for the simulated end-to-end runs (scripts/sim/README.md)."""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
PROGRAM = HERE.parent.parent
HEADERS = {'X-Companion-Client': 'workspace'}


def free_port(start: int) -> int:
    """The first port from `start` nothing listens on, so a run never talks to an app left over from another."""
    for port in range(start, start + 200):
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', port)) != 0:
                return port
    raise RuntimeError(f'no free port from {start}')


def wait_for(url: str, seconds: float = 60):
    end = time.time() + seconds
    while time.time() < end:
        try:
            if httpx.get(url, timeout=2).status_code < 500:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.3)
    raise RuntimeError(f'{url} did not come up')


class Stack:
    """The stand-ins and the apps; `app(name)` starts one on its own data folder and port."""

    def __init__(self, root: Path, model_port=18234, comfy_port=18188, first_port=18801):
        self.root = root
        self.model_port, self.comfy_port = free_port(model_port), free_port(comfy_port)
        self.next_port = first_port
        self.processes = []
        root.mkdir(parents=True, exist_ok=True)
        self.spawn([sys.executable, str(PROGRAM / 'scripts/acceptance/standins.py'), '--model-port', str(model_port),
                    '--comfy-port', str(comfy_port), '--log', str(root / 'model-requests.jsonl')], root / 'standins.log')
        wait_for(f'http://127.0.0.1:{model_port}/v1/models')

    def spawn(self, command, log: Path, env=None):
        handle = open(log, 'w', encoding='utf-8')
        process = subprocess.Popen(command, cwd=PROGRAM, stdout=handle, stderr=subprocess.STDOUT,
                                   env={**os.environ, 'PYTHONPATH': str(PROGRAM), **(env or {})})
        self.processes.append(process)
        return process

    def app(self, name: str) -> str:
        port = free_port(self.next_port)
        self.next_port = port + 1
        data = self.root / name
        data.mkdir(parents=True, exist_ok=True)
        self.spawn([sys.executable, str(PROGRAM / 'scripts/acceptance/serve.py'), '--port', str(port)],
                   self.root / f'{name}.log', env={'COMPANION_DATA_DIR': str(data), 'COMPANION_API_KEY': 'stand-in'})
        url = f'http://127.0.0.1:{port}'
        wait_for(f'{url}/api/health')
        return url

    def model_url(self) -> str:
        return f'http://127.0.0.1:{self.model_port}/v1'

    def stop(self):
        for process in self.processes:
            process.terminate()
        for process in self.processes:
            try:
                process.wait(10)
            except subprocess.TimeoutExpired:
                process.kill()
