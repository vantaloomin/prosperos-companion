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

from companion.database import decode, many
from companion.images import backends
from companion.images.adapters.comfyui import default_files
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
# diffusion model's file name. Krea 2 is the target (docs/images.md); other models are similar or smaller.
IMAGE_GB = [(r'(nv|mx)?fp4|int4|svdq', 11.0), (r'gguf|q[2-6]_', 12.0), (r'fp8|e4m3|e5m2', 16.0)]
FULL_IMAGE_GB = 24.0
NVFP4_IMAGE_GB = IMAGE_GB[0][1]
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
    name = unet.lower()
    return next((value for pattern, value in IMAGE_GB if re.search(pattern, name)), FULL_IMAGE_GB)


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
    picture = NVFP4_IMAGE_GB
    if alone:
        lines.append(f'Text: local models up to about {alone}B at 4-bit (Q4) fit on the {best["name"]}.')
    else:
        lines.append(f'Text: the {best["name"]} is too small for a useful local text model. Use a hosted service.')
    second = gpus[1] if len(gpus) > 1 else None
    if second and second['usable_gb'] >= picture:
        lines.append(f'Pictures: run ComfyUI on the {second["name"]} (start it with --cuda-device {second["index"]}) '
                     'and keep the text model on the bigger card, so both stay loaded.')
    elif best['usable_gb'] >= picture:
        together = largest_text(best['usable_gb'] - picture)
        if together:
            lines.append(f'Pictures: Krea 2 in a 4-bit file (NVFP4) needs about {gb(picture)}. With it on the same '
                         f'card, keep the text model to about {together}B, or use a hosted image service.')
        else:
            lines.append('Pictures: Krea 2 in a 4-bit file (NVFP4) fits, but not beside a local text model. Use a '
                         'hosted text model with local pictures, or a hosted image service.')
    else:
        lines.append(f'Pictures: the card is too small for Krea 2 (about {gb(picture)} even in a 4-bit file). '
                     'Use a hosted image service.')
    return lines


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
        unet = config.get('unet_name') or default_files()['unet_name']
        found.append({'label': backend['label'], 'base_url': config.get('base_url', ''), 'unet': unet,
                      'size_gb': image_size_gb(unet)})
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
                       f"{card_text(card)}. Pictures will be very slow or fail. "
                       + ('A 4-bit file (NVFP4) or a hosted image service fits better.' if image['size_gb'] > NVFP4_IMAGE_GB
                          else 'A hosted image service fits better.'))
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
        with database.connect() as connection:
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
