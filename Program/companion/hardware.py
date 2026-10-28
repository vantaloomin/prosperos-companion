"""What this computer can run locally, and warnings for setups that will run badly.

The installer prints the summary (`python -m companion.hardware`); Settings > Models and the welcome
screen show it, with warnings checked against the models actually set up: a local text model too big
for the graphics card, or a local text model and local ComfyUI pictures that cannot both fit on it.

Only NVIDIA cards (through nvidia-smi) and Apple silicon (shared memory) are measured. Model sizes are
rough estimates from names and file names, never a promise; the text says "about" for that reason.
Nothing here loads, unloads or starts a model.
"""
import ctypes
import os
import platform
import re
import shutil
import subprocess
import time
from urllib.parse import urlsplit

import httpx

from companion.database import decode, encode, many
from companion.images import backends
from companion.images.adapters.comfyui import EDIT_MODEL, default_files, family_of, model_file
from companion.providers.urls import is_loopback
from companion.text_models import routes

# Bits per weight for common quantizations, as named in GGUF, Ollama and Kobold model names.
BITS = [(r'iq1', 1.8), (r'iq2', 2.5), (r'iq3', 3.4), (r'iq4', 4.4), (r'q2', 2.9), (r'q3', 3.9), (r'q4', 4.8),
        (r'q5', 5.7), (r'q6', 6.6), (r'q8', 8.5), (r'(nv|mx)?fp4|int4|awq|gptq|4bit', 4.5), (r'fp8|int8|8bit', 8.5),
        (r'b?f(p)?16', 16.0)]
# Ollama tags and most local servers default to a 4-bit file when the name gives no quantization.
DEFAULT_BITS = 4.8
CONTEXT_GB = 1.5
# Rough memory for a picture model with its text encoder and working space, by the precision in the
# diffusion model's file name, for models other than Krea 2 (which has its own sizes below).
IMAGE_GB = [(r'(nv|mx)?fp4|int4|svdq', 11.0), (r'gguf|q[2-6]_', 12.0), (r'fp8|e4m3|e5m2', 16.0),
            # Qwen Image 2.1's int8 files with their 8B encoder, Anima (2B), and SDXL-based checkpoints.
            (r'int8|w4a8', 17.0), (r'anima', 6.0), (r'illustrious|pony|noob|sdxl|animagine', 8.0)]
FULL_IMAGE_GB = 24.0
# Krea 2 Turbo's diffusion model in each precision, in GB as the card counts them, from the file sizes on
# Comfy-Org/Krea-2 and the community GGUF repos (read 2026-10-28). ComfyUI moves the text encoder off the card
# while the model draws, so a picture needs the model file plus working room for the picture and the VAE.
KREA2 = re.compile(r'krea|kr2|kera', re.IGNORECASE)
KREA2_WEIGHTS_GB = [(r'bf16|fp16', 24.5), (r'(nv|mx)?fp4', 7.1), (r'mxfp8|int8', 12.6), (r'fp8', 12.2),
                    (r'q8', 12.8), (r'q6', 9.9), (r'q5', 8.3), (r'q4', 7.0), (r'q3', 5.6), (r'q2', 4.6)]
WORKING_GB = 2.0
FP4 = re.compile(r'(nv|mx)?fp4', re.IGNORECASE)
# Cards that run 4-bit NVFP4 files natively (Blackwell: RTX 50-series and its workstation and data-centre kin).
# Elsewhere ComfyUI has to unpack them, so the app doesn't pick them there.
BLACKWELL = re.compile(r'RTX\s*50\d0|RTX PRO \d+ Blackwell|\bB[12]00\b|\bGB[12]\d\d\b', re.IGNORECASE)
# What the app picks for a card too small for the built-in fp8 file, best first: the 4-bit NVFP4 file on a
# Blackwell card, else the largest GGUF that fits (the built-in workflow then loads it with the ComfyUI-GGUF nodes).
KREA2_SMALLER = ['krea2_turbo_nvfp4.safetensors', 'krea2_turbo-Q6_K.gguf', 'krea2_turbo-Q5_K_M.gguf',
                 'krea2_turbo-Q4_K_M.gguf', 'krea2_turbo-Q3_K_M.gguf']
# Krea 2 files that don't suit the built-in Turbo workflow: the slow Raw/Base model and Edit merges.
NOT_TURBO = re.compile(r'raw|base', re.IGNORECASE)
LOW_MEMORY_GB = 16
# macOS lets the GPU use roughly three quarters of shared memory by default (inferred, not measured here).
APPLE_SHARE = 0.75
# Friendly sizes to quote for "text models up to about N B".
SIZES = [3, 4, 7, 8, 12, 14, 20, 24, 27, 30, 32, 49, 70, 120]
CACHE_SECONDS = 300
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def run(command: list[str], timeout=6) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, creationflags=NO_WINDOW)
    except (OSError, subprocess.SubprocessError):
        return ''
    return result.stdout if result.returncode == 0 else ''


def memory_gb() -> float | None:
    """Total system memory."""
    system = platform.system()
    if system == 'Windows':
        class Status(ctypes.Structure):
            _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong), ('total', ctypes.c_ulonglong),
                        ('available', ctypes.c_ulonglong), ('total_page', ctypes.c_ulonglong),
                        ('available_page', ctypes.c_ulonglong), ('total_virtual', ctypes.c_ulonglong),
                        ('available_virtual', ctypes.c_ulonglong), ('available_extended', ctypes.c_ulonglong)]
        status = Status()
        status.length = ctypes.sizeof(Status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return status.total / 2**30
        return None
    if system == 'Darwin':
        found = run(['sysctl', '-n', 'hw.memsize']).strip()
        return int(found) / 2**30 if found.isdigit() else None
    try:
        with open('/proc/meminfo', encoding='utf-8') as file:
            for line in file:
                if line.startswith('MemTotal:'):
                    return int(line.split()[1]) / 2**20
    except (OSError, ValueError, IndexError):
        pass
    return None


def nvidia_gpus(output: str) -> list[dict]:
    """Parse `nvidia-smi --query-gpu=index,name,memory.total,memory.used --format=csv,noheader,nounits`."""
    gpus = []
    for line in output.splitlines():
        parts = [part.strip() for part in line.split(',')]
        if len(parts) < 3:
            continue
        try:
            total = float(parts[2]) / 1024
        except ValueError:
            continue
        try:
            used = float(parts[3]) / 1024 if len(parts) > 3 else None
        except ValueError:
            used = None
        gpus.append({'index': int(parts[0]) if parts[0].isdigit() else len(gpus), 'name': parts[1],
                     'memory_gb': total, 'usable_gb': total, 'used_gb': used, 'shared': False})
    return gpus


def find_gpus(memory: float | None) -> tuple[list[dict], str | None]:
    """Graphics cards with their memory, and a note when none could be measured."""
    smi = shutil.which('nvidia-smi')
    if smi:
        gpus = nvidia_gpus(run([smi, '--query-gpu=index,name,memory.total,memory.used',
                                '--format=csv,noheader,nounits']))
        if gpus:
            return gpus, None
    if platform.system() == 'Darwin' and platform.machine() == 'arm64' and memory:
        name = run(['sysctl', '-n', 'machdep.cpu.brand_string']).strip() or 'Apple silicon'
        return [{'index': 0, 'name': f'{name} (shared memory)', 'memory_gb': memory, 'usable_gb': memory * APPLE_SHARE,
                 'used_gb': None, 'shared': True}], None
    names = []
    if platform.system() == 'Windows':
        names = [line.strip() for line in run(['powershell.exe', '-NoProfile', '-Command',
                 '(Get-CimInstance Win32_VideoController).Name'], timeout=10).splitlines() if line.strip()]
    if names:
        return [], f"Found {', '.join(names)}, but only NVIDIA cards and Apple silicon can be measured, so local model fit is not checked."
    return [], 'No NVIDIA graphics card or Apple silicon found. Local models would run on the processor.'


def scan() -> dict:
    memory = memory_gb()
    gpus, note = find_gpus(memory)
    return {'system': platform.system() or 'Unknown', 'cores': os.cpu_count() or 0, 'memory_gb': memory,
            'gpus': gpus, 'gpu_note': note}


def text_size_gb(model: str) -> float | None:
    """About how much memory a text model takes, from its name ("gemma-4-31b-it-Q4_K_M"), or None."""
    name = model.lower()
    experts = re.search(r'(?<![\w.])(\d+)x(\d+(?:\.\d+)?)b(?![a-z])', name)
    found = re.search(r'(?<![\w.])(\d+(?:\.\d+)?)b(?![a-z])', name)
    if experts:
        billions = int(experts.group(1)) * float(experts.group(2))
    elif found:
        billions = float(found.group(1))
    else:
        return None
    bits = next((value for pattern, value in BITS if re.search(rf'(?<![a-z]){pattern}', name)), DEFAULT_BITS)
    return round(billions * bits / 8 * 1.1 + CONTEXT_GB, 1)


def image_size_gb(unet: str) -> float:
    if KREA2.search(unet):
        weights = next((value for pattern, value in KREA2_WEIGHTS_GB if re.search(pattern, unet, re.IGNORECASE)),
                       KREA2_WEIGHTS_GB[0][1])
        return round(weights + WORKING_GB, 1)
    name = unet.lower()
    return next((value for pattern, value in IMAGE_GB if re.search(pattern, name)), FULL_IMAGE_GB)


def turbo_file(name: str) -> bool:
    """A Krea 2 file the built-in Turbo workflow can load."""
    return bool(KREA2.search(name)) and name.lower().endswith(('.safetensors', '.gguf')) and \
        not NOT_TURBO.search(name) and not EDIT_MODEL.search(name)


def krea_pick(gpu: dict | None, options=None) -> str | None:
    """The Krea 2 file for this card when the built-in fp8 one is too big for it: the best one ComfyUI already has
    that fits (NVFP4 first on a Blackwell card, which runs it fastest), else the best one to download. None keeps the
    built-in file: it fits, or nothing does (or no card was measured)."""
    if gpu is None or image_size_gb(default_files('krea2')['unet_name']) <= gpu['usable_gb']:
        return None
    blackwell = bool(BLACKWELL.search(gpu['name']))

    def fits(name):
        return image_size_gb(name) <= gpu['usable_gb'] and (blackwell or not FP4.search(name))
    have = [name for name in options or [] if turbo_file(name) and fits(name)]
    if have:
        return max(have, key=lambda name: (bool(FP4.search(name)), image_size_gb(name)))
    return next((name for name in KREA2_SMALLER if fits(name)), None)


def best_card(computer: dict) -> dict | None:
    return max(computer['gpus'], key=lambda gpu: gpu['usable_gb'], default=None)


def fit_images(connection, computer: dict, options=None, only: str | None = None):
    """Puts each Krea 2 ComfyUI server on this computer on a model file its graphics card holds (Vanta, 2026-10-28:
    the app decides, the user overrides). The pick is kept as `unet_fit`, which the built-in workflow uses only while
    the user hasn't chosen a model. `options` are the files the server listed, when it was asked; without them an
    earlier pick that still fits stands."""
    card = best_card(computer)
    for backend in backends.ordered(connection):
        config = decode(backend['config'])
        if (only and backend['id'] != only) or not fits_here(backend, config):
            continue
        pick = krea_pick(card, options if options is not None else [config.get('unet_fit') or ''])
        if config.get('unet_fit') == pick:
            continue
        config.pop('unet_fit', None)
        config.update({'unet_fit': pick} if pick else {})
        connection.execute('UPDATE image_backends SET config=? WHERE id=?', (encode(config), backend['id']))


def fits_here(backend: dict, config: dict) -> bool:
    """A ComfyUI server on this computer running the built-in Krea 2 workflow, whose card the app can measure."""
    return backend['kind'] == 'comfyui' and family_of(config) == 'krea2' and not config.get('workflow') and \
        is_loopback(urlsplit(config.get('base_url', '')).hostname)


def largest_text(card_gb: float) -> int | None:
    """The biggest friendly size (in billions) of a 4-bit text model that fits in this much memory."""
    fitting = [size for size in SIZES if size * DEFAULT_BITS / 8 * 1.1 + CONTEXT_GB <= card_gb]
    return fitting[-1] if fitting else None


def gb(value: float) -> str:
    return f'{value:.0f} GB' if value >= 10 else f'{value:.1f} GB'


def card_text(gpu: dict) -> str:
    return f"{gpu['name']}, {gb(gpu['memory_gb'])}"


def can_run(computer: dict) -> list[str]:
    """Plain lines on what this computer can run locally, before any model is set up."""
    gpus = sorted(computer['gpus'], key=lambda gpu: gpu['usable_gb'], reverse=True)
    lines = []
    if not gpus:
        lines.append('Local models would run on the processor, so replies would be slow. A hosted service '
                     '(OpenAI, Anthropic, OpenRouter, NanoGPT) or your Codex login is the comfortable choice.')
        lines.append('Pictures: use a hosted image service.')
        return lines
    best = gpus[0]
    alone = largest_text(best['usable_gb'])
    file = krea_pick(best) or default_files('krea2')['unet_name']
    picture = image_size_gb(file)
    if alone:
        lines.append(f'Text: local models up to about {alone}B at 4-bit (Q4) fit on the {best["name"]}.')
    else:
        lines.append(f'Text: the {best["name"]} is too small for a useful local text model. Use a hosted service.')
    second = gpus[1] if len(gpus) > 1 else None
    if second and second['usable_gb'] >= picture:
        lines.append(f'Pictures: run ComfyUI on the {second["name"]} (start it with --cuda-device {second["index"]}) '
                     'and keep the text model on the bigger card, so both stay loaded.')
    elif best['usable_gb'] >= picture:
        lines.append(picture_line(best, file, picture))
    else:
        lines.append(f'Pictures: the card is too small for Krea 2 (about {gb(image_size_gb(KREA2_SMALLER[-1]))} even in '
                     'a 3-bit file). Use a hosted image service.')
    return lines


def picture_line(best: dict, file: str, picture: float) -> str:
    together = largest_text(best['usable_gb'] - picture)
    if together:
        return (f'Pictures: Krea 2 ({file}) needs about {gb(picture)}. With it on the same card, keep the text model '
                f'to about {together}B, or use a hosted image service.')
    return (f'Pictures: Krea 2 ({file}) fits, but not beside a local text model. Use a hosted text model with local '
            'pictures, or a hosted image service.')


def local_text(connection) -> list[dict]:
    """Text profiles that run on this computer and do at least one job."""
    used = set(routes(connection).values())
    found = []
    for row in many(connection, 'SELECT id, name, config FROM model_profiles ORDER BY name'):
        config = decode(row['config'])
        if row['id'] not in used or config.get('purpose') == 'recall' or not config.get('model'):
            continue
        host = urlsplit(config.get('base_url') or '').hostname
        if config['provider'] in {'local', 'kobold'} or (config['provider'] == 'compatible' and is_loopback(host)):
            found.append({'profile': row['name'], 'model': config['model'], 'size_gb': text_size_gb(config['model'])})
    return found


def local_images(connection) -> list[dict]:
    """Enabled ComfyUI backends on this computer, with the diffusion model each one loads."""
    found = []
    for backend in backends.ordered(connection, enabled_only=True):
        if backend['kind'] != 'comfyui' or not is_loopback(urlsplit(decode(backend['config']).get('base_url', '')).hostname):
            continue
        config = decode(backend['config'])
        unet = model_file(config)
        found.append({'label': backend['label'], 'base_url': config.get('base_url', ''), 'unet': unet,
                      'size_gb': image_size_gb(unet), 'krea2': family_of(config) == 'krea2'})
    return found


def comfy_device(base_url: str) -> str | None:
    """The card ComfyUI says it uses ("cuda:1 NVIDIA GeForce RTX 4090 : cudaMallocAsync"), or None."""
    try:
        response = httpx.get(base_url.rstrip('/') + '/system_stats', timeout=2, trust_env=False)
        devices = response.json().get('devices') or []
        return devices[0].get('name') if devices else None
    except (httpx.HTTPError, ValueError, AttributeError):
        return None


def device_index(name: str | None) -> int | None:
    found = re.match(r'cuda:(\d+)', name or '')
    return int(found.group(1)) if found else None


def warning(area: str, text: str, tone='warning') -> dict:
    return {'area': area, 'tone': tone, 'text': text}


def check(computer: dict, texts: list[dict], images: list[dict], devices: dict[str, str | None]) -> list[dict]:
    """Warnings for the setup in use. `devices` maps a ComfyUI address to the card it reports."""
    warnings = []
    gpus = sorted(computer['gpus'], key=lambda gpu: gpu['usable_gb'], reverse=True)
    memory = computer['memory_gb']
    if memory and memory < LOW_MEMORY_GB and (texts or images):
        warnings.append(warning('computer', f'This computer has {gb(memory)} of memory. Local models need room beyond '
                                'the graphics card; expect slowdowns. 32 GB or more is comfortable.'))
    if not gpus:
        if texts and not (computer['gpu_note'] or '').startswith('Found'):
            warnings.append(warning('text', f"{texts[0]['model']} runs on the processor here, so replies will be "
                                    'slow. A hosted service gives a much better experience on this computer.'))
        return warnings
    warnings += [found for text in texts if (found := text_warning(text, gpus[0], memory))]
    biggest = max((text['size_gb'] or 0 for text in texts), default=0)
    warnings += [found for image in images if (found := image_warning(image, gpus, biggest, devices))]
    return warnings


def text_warning(text: dict, best: dict, memory: float | None) -> dict | None:
    if text['size_gb'] is None:
        return warning('text', f"Couldn't tell the size of {text['model']} from its name, so it isn't checked "
                       'against your graphics card.', 'tip')
    if text['size_gb'] <= best['usable_gb']:
        return None
    fits = largest_text(best['usable_gb'])
    spill = 'and may not load at all' if memory and text['size_gb'] > best['usable_gb'] + memory * 0.8 else \
        'so part of it runs from system memory and replies will be slow'
    return warning('text', f"{text['model']} needs about {gb(text['size_gb'])}, more than the {card_text(best)}, "
                   f"{spill}. " + (f'A model of about {fits}B at 4-bit fits.' if fits else 'Consider a hosted service.'))


def image_warning(image: dict, gpus: list[dict], biggest: float, devices: dict[str, str | None]) -> dict | None:
    """Pictures too big for their card, or a local text model and pictures that can't share it."""
    best = gpus[0]
    index = device_index(devices.get(image['base_url']))
    card = next((gpu for gpu in gpus if gpu['index'] == index), best)
    if image['size_gb'] > card['usable_gb']:
        return warning('images', f"{image['label']}: {image['unet']} needs about {gb(image['size_gb'])}, more than the "
                       f"{card_text(card)}. ComfyUI keeps the rest in system memory, so pictures will be slow. "
                       + smaller_text(card, image.get('krea2', False)))
    if not biggest or biggest + image['size_gb'] <= best['usable_gb']:
        return None
    others = [gpu for gpu in gpus[1:] if gpu['usable_gb'] >= image['size_gb']]
    if not others:
        together = largest_text(best['usable_gb'] - image['size_gb'])
        return warning('images', f"Your text model (about {gb(biggest)}) and {image['label']} (about "
                       f"{gb(image['size_gb'])}) don't both fit on the {card_text(best)}. Pictures will be very slow "
                       'or fail while the text model is loaded. '
                       + (f'A text model of about {together}B at 4-bit leaves room, or use '
                          if together else 'Use a hosted text model, or ') + 'a hosted image service for pictures.')
    if index is not None and index != best['index']:
        return None
    other = others[0]
    return warning('images', f"Your text model and {image['label']} don't both fit on the {card_text(best)}"
                   + (', and ComfyUI reports it is on that card' if index is not None else '')
                   + f". Start ComfyUI with --cuda-device {other['index']} so pictures use the {other['name']}, and "
                   'keep the text model on the bigger card.', 'warning' if index is not None else 'tip')


def smaller_text(card: dict, krea2: bool) -> str:
    """What fits the card instead: a named Krea 2 file, else a hosted service."""
    pick = krea_pick(card) if krea2 else None
    if not pick:
        return 'A hosted image service fits better.'
    nodes = ' with the ComfyUI-GGUF nodes' if pick.endswith('.gguf') else ''
    return f'{pick} (about {gb(image_size_gb(pick))}) fits{nodes}; pick it under Model files, or use a hosted image service.'


class Hardware:
    """Scans once and keeps the result for a few minutes; the scan runs nvidia-smi."""

    def __init__(self, scanner=scan, device=comfy_device):
        self.scanner = scanner
        self.device = device
        self.cached: tuple[float, dict] | None = None

    def computer(self, fresh=False) -> dict:
        if fresh or not self.cached or time.monotonic() - self.cached[0] > CACHE_SECONDS:
            self.cached = (time.monotonic(), self.scanner())
        return self.cached[1]

    def report(self, database, fresh=False) -> dict:
        computer = self.computer(fresh)
        with database.connect(write=True) as connection:
            fit_images(connection, computer)
            texts = local_text(connection)
            images = local_images(connection)
        devices = {image['base_url']: self.device(image['base_url']) for image in images} if len(computer['gpus']) > 1 else {}
        return {'computer': computer, 'can_run': can_run(computer), 'local_text': texts, 'local_images': images,
                'warnings': check(computer, texts, images, devices)}


def summary(computer: dict) -> str:
    memory = f"{gb(computer['memory_gb'])} memory" if computer['memory_gb'] else 'memory unknown'
    lines = [f"This computer: {computer['system']}, {computer['cores']} processor threads, {memory}."]
    lines += [f"Graphics: {card_text(gpu)}" for gpu in computer['gpus']]
    if computer['gpu_note']:
        lines.append(computer['gpu_note'])
    return '\n'.join(lines + can_run(computer))


if __name__ == '__main__':
    print(summary(scan()))
