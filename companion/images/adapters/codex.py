"""The Codex/ChatGPT subscription path through the `chatgpt-imagegen` CLI (PRD F8).

Modelled on Darling Blades' `scripts/gen-card-art.ts`: one subprocess per image with the prompt,
an output path, one of the three verified sizes and a 300-second budget. The CLI authenticates
with the token `codex login` stored; this app never reads, stores or exports it, and only checks
that the login file exists.

Requests run strictly one at a time (parallel calls racing the token refresh invalidated the
credential in Darling Blades). An authentication error stops the Codex queue until the user signs
in again. The raw output stays on disk until it passes the image check, and nothing is retried
automatically: each call spends subscription quota.
"""
import asyncio
import os
import shutil
import sys
from pathlib import Path

from companion.images.adapters.base import AdapterError, Check, ImageResult

TIMEOUT_SECONDS = 300
VERIFIED_SIZES = {(1024, 1024), (1536, 1024), (1024, 1536)}
LOGIN_STEP = 'Run "codex login" in a terminal on this computer, then choose "Signed in again" in Settings.'
AUTH_SIGNS = ('auth.json', 'codex login', 'access_token', 'refresh_token', 'token refresh', 'http 401', 'http 403',
              'unauthorized')
REFUSAL_SIGNS = ('content policy', 'content_policy', 'safety system', 'moderation', 'policy violation')
SERIAL = asyncio.Lock()


def codex_home() -> Path:
    return Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex')


def logged_in() -> bool:
    return (codex_home() / 'auth.json').is_file()


def locate(config) -> str | None:
    configured = (config.get('cli_path') or '').strip()
    if configured:
        return configured if Path(configured).is_file() else None
    return shutil.which('chatgpt-imagegen')


def command(cli: str) -> list[str]:
    """The CLI is a Python script; run it with this interpreter unless it is a native launcher."""
    if Path(cli).suffix.lower() in {'.exe', '.cmd', '.bat'}:
        return [cli]
    return [sys.executable, cli]


def failure(stderr: str) -> AdapterError:
    text = stderr.strip().splitlines()[-1] if stderr.strip() else 'no error output'
    lowered = stderr.casefold()
    if any(sign in lowered for sign in AUTH_SIGNS):
        return AdapterError('auth', f'Codex sign-in failed or expired ({text}). The Codex queue is stopped. '
                            f'{LOGIN_STEP}')
    if any(sign in lowered for sign in REFUSAL_SIGNS):
        return AdapterError('refused', f'OpenAI refused this image ({text}).')
    if 'http 429' in lowered:
        return AdapterError('rate_limited', 'Your ChatGPT image quota is used up for now. Try again later.')
    if 'timed out' in lowered or 'stalled' in lowered:
        return AdapterError('timeout', f'Codex image generation timed out ({text}).')
    return AdapterError('failed', f'Codex image generation failed: {text}')


class CodexAdapter:
    def __init__(self, timeout_seconds=TIMEOUT_SECONDS):
        self.timeout_seconds = timeout_seconds

    async def generate(self, request) -> ImageResult:
        cli = locate(request.config)
        if cli is None:
            raise AdapterError('unavailable', 'The chatgpt-imagegen CLI was not found. Set its location in Settings.')
        if not logged_in():
            raise AdapterError('auth', f'Codex is not signed in on this computer. {LOGIN_STEP}')
        if (request.width, request.height) not in VERIFIED_SIZES:
            raise AdapterError('incompatible', 'Codex only makes 1024x1024, 1536x1024 or 1024x1536 images.')
        raw = request.raw_dir / f'{request.job_id}.png'
        args = [*command(cli), request.prompt, '-o', str(raw), '--size', f'{request.width}x{request.height}',
                '--format', 'png', '--quiet', '--no-progress', '--timeout', str(self.timeout_seconds)]
        async with SERIAL:
            stderr = await self.run(args)
        if not raw.is_file():
            raise failure(stderr)
        return ImageResult(raw.read_bytes(), model='ChatGPT image generation', workflow='chatgpt-imagegen',
                           raw_path=raw)

    async def run(self, args) -> str:
        process = await asyncio.create_subprocess_exec(*args, stdin=asyncio.subprocess.DEVNULL,
                                                       stdout=asyncio.subprocess.PIPE,
                                                       stderr=asyncio.subprocess.PIPE)
        try:
            async with asyncio.timeout(self.timeout_seconds + 30):
                _stdout, stderr = await process.communicate()
        except TimeoutError as error:
            await self.stop(process)
            raise AdapterError('timeout', 'Codex image generation did not finish in time; it was stopped.') from error
        except asyncio.CancelledError:
            await self.stop(process)
            raise
        text = stderr.decode('utf-8', 'replace')
        if process.returncode != 0:
            raise failure(text)
        return text

    @staticmethod
    async def stop(process):
        """Stops only the process this app started."""
        if process.returncode is None:
            process.kill()
            await process.wait()

    async def check(self, backend, config, key=None) -> Check:
        """Finds the CLI and the login file and asks the CLI for its version; spends no quota."""
        cli = locate(config)
        if cli is None:
            return Check(False, 'The chatgpt-imagegen CLI was not found.',
                         ['Install it, or enter the full path to the chatgpt-imagegen script.'])
        details = [f'CLI: {cli}']
        try:
            process = await asyncio.create_subprocess_exec(*command(cli), '--version', stdout=asyncio.subprocess.PIPE,
                                                           stderr=asyncio.subprocess.PIPE)
            async with asyncio.timeout(20):
                stdout, _ = await process.communicate()
            details.append(stdout.decode('utf-8', 'replace').strip() or 'version unknown')
        except (OSError, TimeoutError):
            return Check(False, 'The chatgpt-imagegen CLI could not be started.', details)
        if not logged_in():
            return Check(False, 'Codex is not signed in on this computer.', [*details, LOGIN_STEP])
        return Check(True, 'The CLI is installed and a Codex login exists. This path is experimental.', details)
