"""The trainer adapter: AI Toolkit (ostris/ai-toolkit) training Krea 2 adapters.

NOT VERIFIED ON HARDWARE. The config below was written against AI Toolkit commit ecee894
(2026-09-27): its built-in `krea2` architecture (`extensions_built_in/diffusion_models/krea2`),
the `sd_trainer` process, and the layout of `config/examples/train_lora_qwen_image_24gb.yaml`,
which uses the same Qwen image VAE. It has only been run against a stand-in trainer in the tests.

What the app relies on, all read from that commit:
- `python run.py <config>` runs a job; `.json` configs are accepted (`toolkit/config.py`).
- Checkpoints are saved as `<training_folder>/<name>/<name>_<step, 9 digits>.safetensors`, and
  the finished adapter as `<name>.safetensors` in the same folder.
- Run again with the same name and folder, it resumes from the newest file there (by creation
  time), so the app moves damaged checkpoints aside before resuming.
- Progress is a tqdm bar on the console: `<name>:  12%|...| 120/1500 [...]`.

The app never installs AI Toolkit or downloads weights. AI Toolkit itself fetches whatever the
config names from Hugging Face when it is not cached, which is why Configure discloses it.
"""
import re
from dataclasses import dataclass
from pathlib import Path

NAME = 'AI Toolkit (ostris/ai-toolkit)'
KEY = 'ai-toolkit'
TESTED = 'commit ecee894 (2026-09-27)'
VERIFIED = False
ARCH = 'krea2'
DEFAULT_BASE = 'krea/Krea-2-Raw'
PROGRESS = re.compile(r'(\d+)/(\d+) \[')
CHECKPOINT = re.compile(r'_(\d{9})\.safetensors$')

DEFAULTS = {'network': 'lokr', 'rank': 16, 'steps': 1500, 'learning_rate': 1e-4, 'save_every': 250,
            'resolution': 1024, 'low_vram': False}

DISCLOSURE = (
    'Training runs on this computer through AI Toolkit; your pictures and captions do not leave it. '
    'AI Toolkit downloads anything the configuration names that is not already in its Hugging Face cache: '
    'the base model (Krea 2 Raw is gated, so accept its license on Hugging Face and put HF_TOKEN in AI '
    "Toolkit's .env), the Qwen3-VL 4B text encoder and the Qwen image VAE. Expect tens of gigabytes the first "
    'time. A local folder path as the base model avoids the base model download.')

REQUIREMENTS = [
    'Not verified on hardware. Community reports for Krea 2 training, not tested here:',
    'An NVIDIA GPU with 16 to 24 GB of memory; about 18 to 20 GB at 768 px, out of memory at 1280 px on 24 GB.',
    'About 40 to 45 minutes on an RTX 3090; a 12 GB card has taken 18 hours for 3,000 steps.',
    'Disk: the base model is about 25 GB in BF16, plus the text encoder, cached latents and checkpoints.',
    'Step counts are disputed (500 to 3,500); 3,000 or more is reported to overfit.',
]

CONTROL = ('Training cannot pause. Cancelling stops the trainer process; checkpoints already saved stay and can be '
           'resumed. Chat keeps working, but if your chat model runs on the same GPU both will slow down or run '
           'out of memory. ComfyUI images on this computer wait until training ends.')


@dataclass
class Checkpoint:
    step: int
    path: Path
    final: bool = False


def config(run_name: str, dataset_dir: Path, output_dir: Path, options: dict, base_model: str) -> dict:
    if options['network'] == 'lokr':
        network = {'type': 'lokr', 'lokr_full_rank': True, 'lokr_factor': -1}
    else:
        network = {'type': 'lora', 'linear': options['rank'], 'linear_alpha': options['rank']}
    resolution = [512] if options['resolution'] == 512 else [512, 1024]
    return {'job': 'extension', 'config': {'name': run_name, 'process': [{
        'type': 'sd_trainer', 'training_folder': str(output_dir), 'device': 'cuda:0', 'network': network,
        'save': {'dtype': 'float16', 'save_every': options['save_every'], 'max_step_saves_to_keep': 4},
        'datasets': [{'folder_path': str(dataset_dir), 'caption_ext': 'txt', 'caption_dropout_rate': 0.05,
                      'shuffle_tokens': False, 'cache_latents_to_disk': True, 'resolution': resolution}],
        'train': {'batch_size': 1, 'steps': options['steps'], 'gradient_accumulation': 1, 'train_unet': True,
                  'train_text_encoder': False, 'gradient_checkpointing': True, 'noise_scheduler': 'flowmatch',
                  'optimizer': 'adamw8bit', 'lr': options['learning_rate'], 'dtype': 'bf16',
                  'cache_text_embeddings': True, 'disable_sampling': True},
        'model': {'name_or_path': base_model, 'arch': ARCH, 'quantize': True, 'quantize_te': True,
                  'low_vram': options['low_vram']}}]},
        'meta': {'name': '[name]', 'version': '1.0', 'made_by': 'Prospero Companion'}}


def command(python_path: str, config_path: Path) -> list[str]:
    return [python_path, 'run.py', str(config_path)]


def progress(text: str) -> tuple[int, int] | None:
    """The last step count the console reported, or None when it reported none."""
    found = PROGRESS.findall(text)
    if not found:
        return None
    step, total = found[-1]
    return int(step), int(total)


def checkpoints(output_dir: Path, run_name: str, steps: int) -> list[Checkpoint]:
    folder = output_dir / run_name
    found = []
    if not folder.is_dir():
        return found
    for path in folder.glob(f'{run_name}*.safetensors'):
        if path.name == f'{run_name}.safetensors':
            found.append(Checkpoint(steps, path, final=True))
        elif match := CHECKPOINT.search(path.name):
            found.append(Checkpoint(int(match.group(1)), path))
    return sorted(found, key=lambda item: (item.step, item.final))


def check(python_path: str, trainer_dir: str) -> dict:
    """What can be confirmed without running anything."""
    problems, notes = [], []
    if not python_path:
        problems.append("Name the Python interpreter of your AI Toolkit install (its venv's python).")
    elif not Path(python_path).is_file():
        problems.append(f'{python_path} does not exist.')
    if not trainer_dir:
        problems.append('Name the folder where AI Toolkit is checked out.')
    elif not (Path(trainer_dir) / 'run.py').is_file():
        problems.append(f'{trainer_dir} has no run.py; it does not look like an AI Toolkit checkout.')
    elif not (Path(trainer_dir) / 'extensions_built_in' / 'diffusion_models' / 'krea2').is_dir():
        notes.append('This AI Toolkit checkout has no krea2 model support; update it to a version from late '
                     'September 2026 or newer.')
    return {'ok': not problems, 'problems': problems, 'notes': notes}


def describe() -> dict:
    return {'key': KEY, 'name': NAME, 'tested': TESTED, 'verified': VERIFIED, 'arch': ARCH,
            'default_base_model': DEFAULT_BASE, 'disclosure': DISCLOSURE, 'requirements': REQUIREMENTS,
            'control': CONTROL, 'defaults': DEFAULTS, 'adapter_formats': ['lokr', 'lora']}
