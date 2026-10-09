"""Local programs the Companion can start: LM Studio, Ollama, KoboldCpp and ComfyUI (Settings > Models).

Which programs are in use comes from the model profiles and image backends on this computer. Where each one
is installed is looked up in the usual places; the user types a path only when it is not found. The command
for each uses what the Companion already has: the profile's address, model and context size, and ComfyUI's
port. Nothing here downloads or installs anything.
"""
import os
import shutil
import sys
from pathlib import Path
from urllib.parse import urlsplit

from companion.database import decode, many
from companion.providers.urls import is_loopback

PROGRAMS = {
    'lmstudio': {'label': 'LM Studio', 'port': 1234, 'health': '/v1/models'},
    'ollama': {'label': 'Ollama', 'port': 11434, 'health': '/api/tags'},
    'kobold': {'label': 'KoboldCpp', 'port': 5001, 'health': '/api/v1/model'},
    'comfyui': {'label': 'ComfyUI', 'port': 8188, 'health': '/system_stats'},
}
# Text models first, then pictures, so a slow model load never races ComfyUI for the graphics card.
ORDER = ('lmstudio', 'ollama', 'kobold', 'comfyui')
PORTS = {1234: 'lmstudio', 11434: 'ollama', 5001: 'kobold'}
SCAN_LIMIT = 4000
WINDOWS = sys.platform == 'win32'


def text_program(config: dict) -> str | None:
    """The program behind a local text or recall profile, from its provider and port."""
    address = urlsplit(config.get('base_url') or '')
    if config.get('provider') not in {'local', 'kobold', 'compatible'} or not is_loopback(address.hostname):
        return None
    if config['provider'] == 'kobold':
        return 'kobold'
    return PORTS.get(address.port or 0, 'lmstudio' if config['provider'] == 'local' else None)


def profile_uses(connection) -> list[dict]:
    found = []
    for row in many(connection, 'SELECT id, name, config FROM model_profiles ORDER BY name COLLATE NOCASE'):
        config = decode(row['config'])
        program = text_program(config)
        if program:
            found.append({'program': program, 'kind': 'profile', 'id': row['id'], 'name': row['name'],
                          'port': urlsplit(config['base_url']).port or PROGRAMS[program]['port'],
                          'model': config.get('model') or '', 'context_tokens': config.get('context_tokens')})
    return found


def image_uses(connection) -> list[dict]:
    found = []
    for row in many(connection, "SELECT id, label, config FROM image_backends WHERE kind='comfyui' ORDER BY position"):
        address = urlsplit(decode(row['config']).get('base_url') or '')
        if is_loopback(address.hostname):
            found.append({'program': 'comfyui', 'kind': 'image', 'id': row['id'], 'name': row['label'],
                          'port': address.port or PROGRAMS['comfyui']['port'], 'model': '', 'context_tokens': None})
    return found


def uses(connection) -> dict[str, list[dict]]:
    """Each program in use on this computer, with the profiles and image backends that use it, in ORDER."""
    every = profile_uses(connection) + image_uses(connection)
    return {program: [use for use in every if use['program'] == program]
            for program in ORDER if any(use['program'] == program for use in every)}


def home_places() -> list[Path]:
    home = Path.home()
    places = [home, home / 'Desktop', home / 'Documents', home / 'Downloads']
    if WINDOWS:
        local = Path(os.environ.get('LOCALAPPDATA', home / 'AppData' / 'Local'))
        places += [local / 'Programs', *(Path(f'{letter}:\\') for letter in 'CDEFGZ' if Path(f'{letter}:\\').is_dir())]
    else:
        places += [Path('/Applications'), Path('/opt')]
    return [place for place in places if place.is_dir()]


def search(places: list[Path], matches, depth=2) -> Path | None:
    """The first path under `places` (a few levels down) that `matches`, giving up after SCAN_LIMIT entries."""
    seen = 0
    for place in places:
        level = [place]
        for _ in range(depth + 1):
            following = []
            for folder in level:
                try:
                    entries = sorted(folder.iterdir())
                except OSError:
                    continue
                seen += len(entries)
                found = next((entry for entry in entries if matches(entry)), None)
                if found or seen > SCAN_LIMIT:
                    return found
                following += [entry for entry in entries if entry.is_dir() and not entry.name.startswith(('.', '$'))]
            level = following
    return None


def first_file(*paths: Path) -> Path | None:
    return next((path for path in paths if path.is_file()), None)


def find_lmstudio() -> Path | None:
    name = 'lms.exe' if WINDOWS else 'lms'
    home = Path.home()
    found = shutil.which('lms')
    return Path(found) if found else first_file(home / '.lmstudio' / 'bin' / name, home / '.cache' / 'lm-studio' / 'bin' / name)


def find_ollama() -> Path | None:
    found = shutil.which('ollama')
    local = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    return Path(found) if found else first_file(local / 'Programs' / 'Ollama' / 'ollama.exe', Path('/usr/local/bin/ollama'),
                                                Path('/Applications/Ollama.app/Contents/Resources/ollama'))


def is_kobold(entry: Path) -> bool:
    name = entry.name.lower()
    return entry.is_file() and name.startswith('koboldcpp') and (name.endswith('.exe') or not WINDOWS) and '.' not in name.removesuffix('.exe')


def find_kobold() -> Path | None:
    found = shutil.which('koboldcpp')
    return Path(found) if found else search(home_places(), is_kobold)


def is_comfy_folder(entry: Path) -> bool:
    return entry.is_dir() and ((entry / 'python_embeded').is_dir() or ((entry / 'main.py').is_file() and (entry / 'comfy').is_dir()))


def find_comfyui() -> Path | None:
    local = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    desktop = first_file(local / 'Programs' / '@comfyorgcomfyui-electron' / 'ComfyUI.exe', local / 'Programs' / 'ComfyUI' / 'ComfyUI.exe')
    if desktop:
        return desktop
    if Path('/Applications/ComfyUI.app').is_dir():
        return Path('/Applications/ComfyUI.app')
    return search(home_places(), is_comfy_folder)


FINDERS = {'lmstudio': find_lmstudio, 'ollama': find_ollama, 'kobold': find_kobold, 'comfyui': find_comfyui}


def gguf_named(model: str) -> Path | None:
    """The model file KoboldCpp reported as `koboldcpp/<name>`, in LM Studio's or the usual folders."""
    stem = model.removeprefix('koboldcpp/').lower()
    if not stem:
        return None
    home = Path.home()
    places = [home / '.lmstudio' / 'models', home / '.cache' / 'lm-studio' / 'models', *home_places()]
    return search([place for place in places if place.is_dir()],
                  lambda entry: entry.suffix.lower() == '.gguf' and entry.stem.lower() == stem and entry.is_file(), depth=4)


def comfy_python(folder: Path) -> Path | None:
    names = ('Scripts/python.exe',) if WINDOWS else ('bin/python3', 'bin/python')
    return first_file(*(folder / venv / name for venv in ('venv', '.venv') for name in names))


def comfy_command(install: Path, port: int) -> list[str]:
    if install.suffix.lower() in {'.exe', '.app'}:
        # The ComfyUI desktop app keeps its own port; it is started as it is.
        return ['open', '-a', str(install)] if install.suffix == '.app' else [str(install)]
    serve = ['--listen', '127.0.0.1', '--port', str(port)]
    if (install / 'python_embeded').is_dir():
        return [str(install / 'python_embeded' / 'python.exe'), '-s', str(install / 'ComfyUI' / 'main.py'),
                '--windows-standalone-build', *serve]
    return [str(comfy_python(install) or sys.executable), str(install / 'main.py'), *serve]


def kobold_command(install: Path, model_path: str, use: dict) -> list[str]:
    if model_path.lower().endswith('.kcpps'):
        return [str(install), '--config', model_path, '--port', str(use['port']), '--skiplauncher']
    context = ['--contextsize', str(use['context_tokens'])] if use.get('context_tokens') else []
    return [str(install), '--model', model_path, '--port', str(use['port']), '--gpulayers', '-1', '--skiplauncher', *context]


def lmstudio_steps(install: Path, program_uses: list[dict]) -> list[list[str]]:
    """Start LM Studio's server, then load each model the profiles use with their context size."""
    steps = [[str(install), 'server', 'start', '--port', str(program_uses[0]['port'])]]
    loaded = set()
    for use in program_uses:
        if use['model'] and use['model'] not in loaded:
            loaded.add(use['model'])
            context = ['--context-length', str(use['context_tokens'])] if use.get('context_tokens') else []
            steps.append([str(install), 'load', use['model'], *context, '-y'])
    return steps
