"""The built-in voice: Kokoro, read aloud by sherpa-onnx in its own process (docs/voice-notes.md).

Kokoro (Apache 2.0) is a small text-to-speech model that sounds natural on a processor alone. sherpa-onnx (Apache
2.0) ships a ready-made program that reads text with it, so the Companion needs no new Python packages: it downloads
that program and the model from sherpa-onnx's GitHub releases, pinned and checked against their SHA-256, and runs the
program once per voice note, on the processor with a few threads, so it never competes with a chat model or ComfyUI
for the GPU. Models stay outside the Companion's own process, as built-in recall's do.
"""
import asyncio
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import httpx

from companion.errors import DomainError, require

VERSION = '1.13.8'
RELEASES = 'https://github.com/k2-fsa/sherpa-onnx/releases/download'
# Platform -> (path under RELEASES, bytes, sha256). Checked by hand against the releases on 2026-10-09.
RUNTIMES = {
    'windows-x64': (f'v{VERSION}/sherpa-onnx-v{VERSION}-win-x64-shared-MT-Release.tar.bz2', 24805859,
                    '6dffdc715a4465b989446a6105265d2cb345e7101591a17d35534b6758f6e8df'),
    'macos-arm64': (f'v{VERSION}/sherpa-onnx-v{VERSION}-osx-arm64-shared.tar.bz2', 20314448,
                    'b10e5c7e2c30ea03de9c442655d14860d9edc475c6251d58a8f5f06e913a1d56'),
    'macos-x64': (f'v{VERSION}/sherpa-onnx-v{VERSION}-osx-x64-shared.tar.bz2', 22846038,
                  '54aad64acee9d2d596535a6080d6f22602a720af5460e1d50461b1e1b06bee40'),
    'linux-x64': (f'v{VERSION}/sherpa-onnx-v{VERSION}-linux-x64-shared.tar.bz2', 28156791,
                  'c0bdb7907d3a74bba1d55d22bf4d9fa75586cf1530614ebe88a27b9118e015c4'),
}
MODEL = ('tts-models/kokoro-multi-lang-v1_0.tar.bz2', 349906910,
         'c5f7e2d2caf082bc1d20fb70334a61d99d20b484500aad32e7cf84c128ea3298')
MODEL_NAME = 'kokoro-multi-lang-v1_0'
MODEL_FILES = ('model.onnx', 'voices.bin', 'tokens.txt', 'espeak-ng-data')
# A sherpa-onnx-offline-tts and a Kokoro folder of the user's own, for other computers or for testing.
PROGRAM_ENV = 'COMPANION_SHERPA_TTS'
MODEL_ENV = 'COMPANION_KOKORO_MODEL'
DOWNLOAD_SECONDS = 1800
SPEAK_SECONDS = 180


def platform_key() -> str | None:
    machine = platform.machine().lower()
    if sys.platform == 'win32' and machine in {'amd64', 'x86_64'}:
        return 'windows-x64'
    if sys.platform == 'darwin':
        return 'macos-arm64' if machine == 'arm64' else 'macos-x64'
    if sys.platform.startswith('linux') and machine in {'amd64', 'x86_64'}:
        return 'linux-x64'
    return None


def program_name() -> str:
    return 'sherpa-onnx-offline-tts.exe' if sys.platform == 'win32' else 'sherpa-onnx-offline-tts'


def threads() -> int:
    """Half the cores, at most four: a voice note is background work and the PC stays responsive."""
    return max(1, min(4, (os.cpu_count() or 2) // 2))


def command(program: str, model: Path, speaker: int, output: Path, text: str) -> list[str]:
    # Kokoro's British voices (ids 20-27) read with British pronunciation (espeak-ng's 'en' is British English).
    language = 'en' if 20 <= speaker <= 27 else 'en-us'
    return [program, f'--kokoro-model={model / "model.onnx"}', f'--kokoro-voices={model / "voices.bin"}',
            f'--kokoro-tokens={model / "tokens.txt"}', f'--kokoro-data-dir={model / "espeak-ng-data"}',
            f'--kokoro-lang={language}', f'--num-threads={threads()}', f'--sid={speaker}',
            f'--output-filename={output}', text]


def run(arguments: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(arguments, capture_output=True, timeout=SPEAK_SECONDS, check=False,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


class Kokoro:
    """Installs the program and the model, and reads text aloud with them."""

    def __init__(self, folder: Path, transport: httpx.AsyncBaseTransport | None = None, runner=None):
        self.folder = folder
        self.transport = transport
        self.runner = runner or run
        self.downloading = False
        self.error = ''
        self.lock = asyncio.Lock()

    # --- what is installed ---------------------------------------------------------------------

    def program(self) -> str | None:
        own = os.environ.get(PROGRAM_ENV)
        if own:
            return own
        root = self.folder / 'sherpa-onnx' / VERSION
        found = next((path for path in root.rglob(program_name()) if path.is_file()), None) if root.is_dir() else None
        return str(found) if found else None

    def model(self) -> Path | None:
        own = os.environ.get(MODEL_ENV)
        root = Path(own) if own else self.folder / MODEL_NAME
        candidates = [root, *(root.iterdir() if root.is_dir() else ())]
        return next((path for path in candidates if path.is_dir() and all((path / name).exists() for name in
                                                                          MODEL_FILES)), None)

    def ready(self) -> bool:
        return self.program() is not None and self.model() is not None

    def download_mb(self) -> int | None:
        runtime = RUNTIMES.get(platform_key())
        if runtime is None:
            return None
        return round(((0 if self.program() else runtime[1]) + (0 if self.model() else MODEL[1])) / 1e6)

    def status(self) -> dict:
        return {'ready': self.ready(), 'available': platform_key() in RUNTIMES or self.ready(),
                'download_mb': self.download_mb(), 'downloading': self.downloading, 'error': self.error,
                'version': VERSION}

    # --- installing ----------------------------------------------------------------------------

    async def install(self) -> dict:
        """Download what is missing, check each file against its pinned checksum and unpack it."""
        runtime = RUNTIMES.get(platform_key())
        require(runtime is not None or self.ready(), 'There is no built-in voice download for this computer. '
                f'Set {PROGRAM_ENV} and {MODEL_ENV}, or choose OpenAI, ElevenLabs or Google.', 409)
        require(not self.downloading, 'The built-in voice is already downloading.', 409)
        self.downloading, self.error = True, ''
        try:
            if self.program() is None:
                await self.fetch(*runtime, self.folder / 'sherpa-onnx' / VERSION)
            if self.model() is None:
                await self.fetch(*MODEL, self.folder / MODEL_NAME)
        except DomainError as error:
            self.error = error.message
            raise
        finally:
            self.downloading = False
        require(self.ready(), 'The download did not contain the built-in voice.', 502)
        return self.status()

    async def fetch(self, path: str, size: int, digest: str, destination: Path):
        archive = await self.download(path, size, digest)
        await asyncio.to_thread(unpack, archive, destination)

    async def download(self, path: str, size: int, digest: str) -> Path:
        target = self.folder / 'downloads' / Path(path).name
        target.parent.mkdir(parents=True, exist_ok=True)
        hasher, received = hashlib.sha256(), 0
        try:
            async with httpx.AsyncClient(transport=self.transport, timeout=DOWNLOAD_SECONDS, follow_redirects=True,
                                         trust_env=True) as client:
                async with client.stream('GET', f'{RELEASES}/{path}') as response:
                    require(response.status_code == 200, f'The voice download failed ({response.status_code}).', 502)
                    with target.open('wb') as file:
                        async for chunk in response.aiter_bytes():
                            received += len(chunk)
                            require(received <= size, 'The voice download is larger than expected.', 502)
                            hasher.update(chunk)
                            file.write(chunk)
        except httpx.HTTPError as error:
            target.unlink(missing_ok=True)
            raise DomainError('Cannot download the built-in voice. Check your internet connection.', 502) from error
        if received != size or hasher.hexdigest() != digest:
            target.unlink(missing_ok=True)
            raise DomainError('The voice download did not match its checksum, so it was not used.', 502)
        return target

    # --- speaking ------------------------------------------------------------------------------

    async def speak(self, text: str, voice: str, output: Path) -> Path:
        """Read the text in the voice (a Kokoro speaker id) into a WAV file, one note at a time."""
        program, model = self.program(), self.model()
        require(program is not None and model is not None, 'The built-in voice is not downloaded yet.', 409)
        output.parent.mkdir(parents=True, exist_ok=True)
        async with self.lock:
            try:
                done = await asyncio.to_thread(self.runner, command(program, model, int(voice), output, text))
            except (OSError, subprocess.TimeoutExpired) as error:
                raise DomainError(f'The built-in voice could not read the note: {error}', 503) from error
        if done.returncode != 0 or not output.is_file():
            detail = (done.stderr or b'').decode('utf-8', 'replace').strip().splitlines()[-1:] or ['no output']
            output.unlink(missing_ok=True)
            raise DomainError(f'The built-in voice could not read the note: {detail[0][:300]}', 503)
        return output


def unpack(archive: Path, destination: Path):
    staging = destination.with_name(destination.name + '.partial')
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    with tarfile.open(archive) as bundle:
        bundle.extractall(staging, filter='data')
    shutil.rmtree(destination, ignore_errors=True)
    staging.rename(destination)
    archive.unlink(missing_ok=True)
